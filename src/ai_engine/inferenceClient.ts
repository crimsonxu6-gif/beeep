import { CapturedFrame } from "@/types/frame";
import { CompositionMode, GuidanceOutput } from "@/types/guidance";
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
  constructor(public readonly code: string, message: string) {
    super(message);
    this.name = "GuidanceApiError";
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

function serializeInput(input: GuidanceEngineInput): Record<string, unknown> {
  return {
    frame_id: input.frame.frameId,
    timestamp: input.frame.timestamp,
    mode: "composition",
    composition_mode: input.compositionMode,
    target_ratio: "3:4",
    language: "zh-CN",
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

  constructor(private readonly options: ShutterMuseHttpClientOptions) {
    this.endpoint = endpointOrUndefined(options.endpoint);
  }

  async infer(input: GuidanceEngineInput): Promise<AnalyzeResult> {
    if (!this.endpoint) {
      if (this.options.mockEnabled) {
        const guidance = createMockGuidance(input.frame.frameId);
        return { guidance, visionFeatures: null };
      }
      throw new GuidanceApiError("AI_UNAVAILABLE", "AI 暂时不可用");
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.options.timeoutMs);
    try {
      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(serializeInput(input)),
        signal: controller.signal
      });
      const text = await response.text();
      if (!response.ok) {
        let message = response.status >= 500 ? "AI 暂时不可用" : "连接失败";
        try {
          const errorBody = JSON.parse(text) as { error?: { message?: string } };
          message = errorBody.error?.message ?? message;
        } catch {
          // Keep the short user-facing status.
        }
        throw new GuidanceApiError(`HTTP_${response.status}`, message);
      }
      const raw = JSON.parse(text) as unknown;
      return {
        guidance: parseGuidanceJson(text),
        visionFeatures: parseVisionFeatures(raw)
      };
    } catch (error) {
      if (error instanceof GuidanceApiError) throw error;
      if (error instanceof Error && error.name === "AbortError") {
        throw new GuidanceApiError("GUIDANCE_TIMEOUT", "AI 构图超时");
      }
      throw new GuidanceApiError("NETWORK_ERROR", "连接失败");
    } finally {
      clearTimeout(timer);
    }
  }
}
