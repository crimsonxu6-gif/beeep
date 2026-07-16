import { CapturedFrame } from "@/types/frame";
import { CompositionMode, StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { StaleResultGuard } from "@/stability/staleResultGuard";
import { StabilityFilter } from "@/stability/stabilityFilter";
import { GuidanceEngineInput, GuidanceInferenceClient } from "./inferenceClient";
import { GuidanceApiError } from "./inferenceClient";

export interface GuidanceDebugState {
  requestId: string | null;
  latestAcceptedFrameId: number;
  latestProcessedFrameId: number;
  latestRenderedFrameId: number;
  droppedStaleResultCount: number;
  visionLatencyMs: number | null;
  guidanceLatencyMs: number | null;
  totalLatencyMs: number | null;
  guidanceEngine: string | null;
  errorCode: string | null;
  captureMs: number | null;
  preprocessMs: number | null;
  payloadBytes: number | null;
  estimatedRequestBodyBytes: number | null;
  networkAndServerMs: number | null;
  clientNetworkOverheadMs: number | null;
  renderMs: number | null;
  tapToOverlayMs: number | null;
  httpStatus: number | null;
  uploadMode: string | null;
  apiMode: string | null;
  captureSource: string | null;
  sourceDimensions: string | null;
  processedDimensions: string | null;
  sourceBytes: number | null;
  processedImageBytes: number | null;
}

interface GuidancePipelineOptions {
  client: GuidanceInferenceClient;
  stabilityFilter: StabilityFilter;
  allowedFrameLag: number;
  expiresMs: number;
}

export interface GuidancePipelineCallbacks {
  onVisionFeatures?: (features: VisionFeatures | null) => void;
  onStableGuidance?: (guidance: StableGuidance | null) => void;
  onDebugState?: (state: GuidanceDebugState) => void;
  onProcessingChange?: (processing: boolean) => void;
  onError?: (error: Error) => void;
  onSuccess?: () => void;
}

const EMPTY_DEBUG: GuidanceDebugState = {
  requestId: null,
  latestAcceptedFrameId: 0,
  latestProcessedFrameId: 0,
  latestRenderedFrameId: 0,
  droppedStaleResultCount: 0,
  visionLatencyMs: null,
  guidanceLatencyMs: null,
  totalLatencyMs: null,
  guidanceEngine: null,
  errorCode: null,
  captureMs: null,
  preprocessMs: null,
  payloadBytes: null,
  estimatedRequestBodyBytes: null,
  networkAndServerMs: null,
  clientNetworkOverheadMs: null,
  renderMs: null,
  tapToOverlayMs: null,
  httpStatus: null,
  uploadMode: null,
  apiMode: null,
  captureSource: null,
  sourceDimensions: null,
  processedDimensions: null,
  sourceBytes: null,
  processedImageBytes: null
};

export class GuidancePipeline {
  private latestPending: GuidanceEngineInput | null = null;
  private processing = false;
  private active = true;
  private callbacks: GuidancePipelineCallbacks = {};
  private expiryTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly staleGuard: StaleResultGuard;
  private debugState: GuidanceDebugState = { ...EMPTY_DEBUG };

  constructor(private readonly options: GuidancePipelineOptions) {
    this.staleGuard = new StaleResultGuard(options.allowedFrameLag);
  }

  setCallbacks(callbacks: GuidancePipelineCallbacks): void {
    this.callbacks = callbacks;
  }

  acceptFrame(frame: CapturedFrame, compositionMode: CompositionMode): void {
    if (!this.active) return;
    this.staleGuard.accept(frame.frameId);
    this.syncGuardDebug();
    const input = { frame, compositionMode };
    if (this.processing) {
      this.latestPending = input;
      return;
    }
    void this.process(input);
  }

  reset(): void {
    this.latestPending = null;
    this.options.stabilityFilter.reset();
    this.staleGuard.reset();
    this.debugState = { ...EMPTY_DEBUG };
    if (this.expiryTimer) clearTimeout(this.expiryTimer);
    this.expiryTimer = undefined;
    this.callbacks.onStableGuidance?.(null);
    this.callbacks.onVisionFeatures?.(null);
    this.callbacks.onDebugState?.(this.debugState);
  }

  dispose(): void {
    this.active = false;
    this.reset();
    this.callbacks = {};
  }

  private async process(input: GuidanceEngineInput): Promise<void> {
    this.processing = true;
    this.callbacks.onProcessingChange?.(true);
    try {
      const result = await this.options.client.infer(input);
      if (!this.active) return;
      const { guidance, visionFeatures } = result;
      const reliable = this.staleGuard.shouldRender(guidance.frameId);
      this.debugState = {
        ...this.debugState,
        requestId: guidance.requestId,
        visionLatencyMs: guidance.timing.visionMs,
        guidanceLatencyMs: guidance.timing.guidanceMs,
        totalLatencyMs: guidance.timing.totalMs,
        guidanceEngine: guidance.guidanceEngine ?? null,
        errorCode: null,
        captureMs: guidance.clientTiming?.captureMs ?? null,
        preprocessMs: guidance.clientTiming?.preprocessMs ?? null,
        payloadBytes: guidance.clientTiming?.payloadBytes ?? null,
        estimatedRequestBodyBytes: guidance.clientTiming?.estimatedRequestBodyBytes ?? null,
        networkAndServerMs: guidance.clientTiming?.networkAndServerMs ?? null,
        clientNetworkOverheadMs: guidance.clientTiming?.clientNetworkOverheadMs ?? null,
        renderMs: null,
        tapToOverlayMs: null,
        httpStatus: guidance.clientTiming?.httpStatus ?? null,
        uploadMode: guidance.clientTiming?.uploadMode ?? null,
        apiMode: guidance.clientTiming?.apiMode ?? null,
        captureSource: guidance.clientTiming?.captureSource ?? null,
        sourceDimensions: guidance.clientTiming ? `${guidance.clientTiming.sourceWidth}x${guidance.clientTiming.sourceHeight}` : null,
        processedDimensions: guidance.clientTiming ? `${guidance.clientTiming.processedWidth}x${guidance.clientTiming.processedHeight}` : null,
        sourceBytes: guidance.clientTiming?.sourceBytes ?? null,
        processedImageBytes: guidance.clientTiming?.processedImageBytes ?? null
      };
      this.syncGuardDebug();
      if (!reliable) return;
      this.callbacks.onSuccess?.();
      this.callbacks.onVisionFeatures?.(visionFeatures);
      const stable = this.options.stabilityFilter.next(guidance);
      if (stable) {
        const renderedAt = Date.now();
        if (stable.guidance.clientTiming) {
          stable.guidance.clientTiming.overlayRenderedAt = renderedAt;
          stable.guidance.clientTiming.renderMs = Math.max(
            0,
            renderedAt - stable.guidance.clientTiming.responseReceivedAt
          );
          if (stable.guidance.clientTiming.tapTimestamp) {
            stable.guidance.clientTiming.tapToOverlayMs = Math.max(
              0,
              renderedAt - stable.guidance.clientTiming.tapTimestamp
            );
          }
          this.debugState = {
            ...this.debugState,
            renderMs: stable.guidance.clientTiming.renderMs,
            tapToOverlayMs: stable.guidance.clientTiming.tapToOverlayMs ?? null
          };
          this.syncGuardDebug();
        }
        this.callbacks.onStableGuidance?.(stable);
        this.scheduleExpiry();
      }
    } catch (error) {
      if (this.active) {
        const normalized = error instanceof Error ? error : new Error(String(error));
        this.debugState = {
          ...this.debugState,
          errorCode: normalized instanceof GuidanceApiError ? normalized.code : "UNKNOWN_ERROR"
        };
        this.syncGuardDebug();
        this.callbacks.onError?.(normalized);
      }
    } finally {
      this.processing = false;
      if (this.active) this.callbacks.onProcessingChange?.(false);
      const pending = this.latestPending;
      this.latestPending = null;
      if (this.active && pending) void this.process(pending);
    }
  }

  private scheduleExpiry(): void {
    if (this.expiryTimer) clearTimeout(this.expiryTimer);
    this.expiryTimer = setTimeout(() => {
      if (!this.active || !this.options.stabilityFilter.isExpired()) return;
      this.callbacks.onStableGuidance?.(null);
    }, this.options.expiresMs + 20);
  }

  private syncGuardDebug(): void {
    this.debugState = {
      ...this.debugState,
      latestAcceptedFrameId: this.staleGuard.latestAcceptedFrameId,
      latestProcessedFrameId: this.staleGuard.latestProcessedFrameId,
      latestRenderedFrameId: this.staleGuard.latestRenderedFrameId,
      droppedStaleResultCount: this.staleGuard.droppedStaleResultCount
    };
    this.callbacks.onDebugState?.(this.debugState);
  }
}
