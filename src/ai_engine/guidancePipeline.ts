import { CapturedFrame } from "@/types/frame";
import { StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { VisionPreprocessor } from "@/vision/preprocessing";
import { VisionSmoother } from "@/stability/smoothing";
import { StabilityFilter } from "@/stability/stabilityFilter";
import { GuidanceEngineInput, GuidanceInferenceClient } from "./inferenceClient";

interface GuidancePipelineOptions {
  preprocessor: VisionPreprocessor;
  client: GuidanceInferenceClient;
  stabilityFilter: StabilityFilter;
  visionSmoother: VisionSmoother;
  batchSize: number;
  maxBatchDelayMs: number;
  maxQueueSize: number;
}

export interface GuidancePipelineCallbacks {
  onVisionFeatures?: (features: VisionFeatures) => void;
  onStableGuidance?: (guidance: StableGuidance) => void;
  onLatency?: (latencyMs: number) => void;
  onProcessingChange?: (processing: boolean) => void;
  onError?: (error: Error) => void;
}

export class GuidancePipeline {
  private readonly preprocessor: VisionPreprocessor;
  private readonly client: GuidanceInferenceClient;
  private readonly stabilityFilter: StabilityFilter;
  private readonly visionSmoother: VisionSmoother;
  private readonly batchSize: number;
  private readonly maxBatchDelayMs: number;
  private readonly maxQueueSize: number;
  private pending: GuidanceEngineInput[] = [];
  private flushTimer: ReturnType<typeof setTimeout> | undefined;
  private flushing = false;
  private callbacks: GuidancePipelineCallbacks = {};

  constructor(options: GuidancePipelineOptions) {
    this.preprocessor = options.preprocessor;
    this.client = options.client;
    this.stabilityFilter = options.stabilityFilter;
    this.visionSmoother = options.visionSmoother;
    this.batchSize = options.batchSize;
    this.maxBatchDelayMs = options.maxBatchDelayMs;
    this.maxQueueSize = options.maxQueueSize;
  }

  setCallbacks(callbacks: GuidancePipelineCallbacks): void {
    this.callbacks = callbacks;
  }

  async acceptFrame(frame: CapturedFrame): Promise<void> {
    try {
      const rawFeatures = await this.preprocessor.preprocess(frame);
      const visionFeatures = this.visionSmoother.next(rawFeatures);
      this.callbacks.onVisionFeatures?.(visionFeatures);

      this.pending.push({ frame, visionFeatures });
      if (this.pending.length > this.maxQueueSize) {
        this.pending.shift();
      }

      if (this.pending.length >= this.batchSize) {
        await this.flush();
      } else {
        this.scheduleFlush();
      }
    } catch (error) {
      this.callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }

  dispose(): void {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = undefined;
    }
  }

  private scheduleFlush(): void {
    if (this.flushTimer) {
      return;
    }

    this.flushTimer = setTimeout(() => {
      this.flushTimer = undefined;
      void this.flush();
    }, this.maxBatchDelayMs);
  }

  private async flush(): Promise<void> {
    if (this.flushing || this.pending.length === 0) {
      return;
    }

    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = undefined;
    }

    const batch = this.pending.splice(0, this.batchSize);
    const startedAt = Date.now();
    this.flushing = true;
    this.callbacks.onProcessingChange?.(true);

    try {
      const outputs = await this.client.inferBatch(batch);
      outputs.forEach((output) => {
        const stableGuidance = this.stabilityFilter.next(output, Date.now());
        if (stableGuidance) {
          this.callbacks.onStableGuidance?.(stableGuidance);
        }
      });
      this.callbacks.onLatency?.(Date.now() - startedAt);
    } catch (error) {
      this.callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    } finally {
      this.flushing = false;
      this.callbacks.onProcessingChange?.(false);
      if (this.pending.length > 0) {
        this.scheduleFlush();
      }
    }
  }
}
