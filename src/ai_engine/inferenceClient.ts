import { CapturedFrame } from "@/types/frame";
import { CompositionMode, GuidanceOutput, ModelStatus } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { parseGuidanceJson } from "./jsonParser";
import { createMockGuidance } from "./mockGuidance";

export interface GuidanceEngineInput {
  frame: CapturedFrame;
  compositionMode: CompositionMode;
}

export interface AnalyzeResult {
  guidance: GuidanceOutput;
  visionFeatures: VisionFeatures | null;
}

export interface GuidanceInferenceClient {
  infer(input: GuidanceEngineInput): Promise<AnalyzeResult>;
}

export class GuidanceApiError extends Error {
  constructor(public readonly status: ModelStatus) {
    super(status.message);
    this.name = "GuidanceApiError";
  }

  get code(): string {
    return this.status.code;
  }
}

interface ShutterMuseHttpClientOptions {
  endpoint: string | undefined;
  timeoutMs: number;
  mockEnabled: boolean;
}

function endpointOrUndefined(value?: string): string | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  if (trimmed.endsWith("/guidance")) return trimmed.replace(/\/guidance$/, "/v1/analyze");
  return trimmed;
}

function serializeInput(input: GuidanceEngineInput, streamId: string): Record<string, unknown> {
  return {
    frame_id: input.frame.frameId,
    timestamp: input.frame.timestamp,
    mode: "composition",
    composition_mode: input.compositionMode,
    target_ratio: "3:4",
    language: "zh-CN",
    requires_person: true,
    stream_id: streamId,
    image: {
      base64: input.frame.image.base64,
      width: input.frame.image.width,
      height: input.frame.image.height,
      mime_type: input.frame.image.mimeType
    }
  };
}

function parseVisionFeatures(value: unknown): VisionFeatures | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const features = (raw.vision_features ?? raw.visionFeatures) as VisionFeatures | undefined;
  return features ?? null;
}

export class ShutterMuseHttpClient implements GuidanceInferenceClient {
  private readonly endpoint: string | undefined;
  private readonly streamId = `camera_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;

  constructor(private readonly options: ShutterMuseHttpClientOptions) {
    this.endpoint = endpointOrUndefined(options.endpoint);
  }

  async infer(input: GuidanceEngineInput): Promise<AnalyzeResult> {
    if (!this.endpoint) {
      if (this.options.mockEnabled) {
        const guidance = createMockGuidance(input.frame.frameId);
        return { guidance, visionFeatures: null };
      }
      throw new GuidanceApiError({
        code: "AI_UNAVAILABLE",
        message: "AI 暂时无法使用",
        suggestion: "可以稍后再来试试",
        retryable: true,
        severity: "error"
      });
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.options.timeoutMs);
    try {
      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(serializeInput(input, this.streamId)),
        signal: controller.signal
      });
      const text = await response.text();
      if (!response.ok) {
        let status: ModelStatus = {
          code: `HTTP_${response.status}`,
          message: response.status >= 500 ? "AI 暂时无法使用" : "请求没有完成",
          suggestion: "可以稍后再试",
          retryable: response.status >= 500,
          severity: "error"
        };
        try {
          const errorBody = JSON.parse(text) as {
            error?: Partial<ModelStatus>;
          };
          if (errorBody.error?.code && errorBody.error.message) {
            status = {
              code: errorBody.error.code,
              message: errorBody.error.message,
              suggestion: errorBody.error.suggestion ?? "可以稍后再试",
              retryable: errorBody.error.retryable ?? true,
              severity: errorBody.error.severity === "waiting" ? "waiting" : "error"
            };
          }
        } catch {
          // Keep the deterministic fallback status.
        }
        throw new GuidanceApiError(status);
      }
      const raw = JSON.parse(text) as unknown;
      return {
        guidance: parseGuidanceJson(text),
        visionFeatures: parseVisionFeatures(raw)
      };
    } catch (error) {
      if (error instanceof GuidanceApiError) throw error;
      if (error instanceof Error && error.name === "AbortError") {
        throw new GuidanceApiError({
          code: "MODEL_TIMEOUT",
          message: "这次分析花得有点久",
          suggestion: "保持画面稳定，再试一次",
          retryable: true,
          severity: "error"
        });
      }
      throw new GuidanceApiError({
        code: "NETWORK_ERROR",
        message: "网络连接不太稳定",
        suggestion: "检查网络后再试",
        retryable: true,
        severity: "error"
      });
    } finally {
      clearTimeout(timer);
    }
  }
}
