import { CapturedFrame } from "@/types/frame";
import { CompositionMode, GuidanceOutput, ModelStatus } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { parseGuidanceJson } from "./jsonParser";
import { createMockGuidance } from "./mockGuidance";
import { appConfig } from "@/config";

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

function captureFields(input: GuidanceEngineInput, streamId: string): Record<string, unknown> {
  const capture = input.frame.capture;
  return {
    frame_id: input.frame.frameId,
    timestamp: input.frame.timestamp,
    mode: "composition",
    composition_mode: input.compositionMode,
    target_ratio: "3:4",
    language: "zh-CN",
    requires_person: true,
    stream_id: streamId,
    camera_facing: capture?.cameraFacing ?? "unknown",
    image_mirrored: capture?.imageMirrored ?? false,
    device_orientation: capture?.deviceOrientation ?? "unknown",
    preview_width: capture?.previewWidth || undefined,
    preview_height: capture?.previewHeight || undefined,
    tap_timestamp: capture?.tapTimestamp,
    capture_started_at: capture?.captureStartedAt,
    capture_completed_at: capture?.captureCompletedAt,
    preprocess_completed_at: capture?.preprocessCompletedAt
  };
}

async function imageBase64(input: GuidanceEngineInput): Promise<string> {
  if (input.frame.image.base64) return input.frame.image.base64;
  if (!input.frame.image.uri) throw new Error("Analysis image file is missing");
  const { File } = await import("expo-file-system");
  return new File(input.frame.image.uri).base64();
}

async function jsonRequestBody(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): Promise<string> {
  return JSON.stringify({
    ...captureFields(input, streamId),
    upload_mode: "base64_json",
    upload_started_at: uploadStartedAt,
    image: {
      base64: await imageBase64(input),
      width: input.frame.image.width,
      height: input.frame.image.height,
      mime_type: input.frame.image.mimeType,
      original_bytes: input.frame.image.originalBytes,
      processed_bytes: input.frame.image.processedBytes
    }
  });
}

function multipartRequestBody(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): FormData {
  if (!input.frame.image.uri) throw new Error("Analysis image URI is missing");
  const form = new FormData();
  const fields = {
    ...captureFields(input, streamId),
    upload_started_at: uploadStartedAt,
    image_width: input.frame.image.width,
    image_height: input.frame.image.height,
    original_bytes: input.frame.image.originalBytes,
    processed_bytes: input.frame.image.processedBytes
  };
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined) form.append(key, String(value));
  }
  form.append(
    "image",
    {
      uri: input.frame.image.uri,
      name: `analysis-${input.frame.frameId}.jpg`,
      type: input.frame.image.mimeType
    } as unknown as Blob
  );
  return form;
}

function estimateMultipartBodyBytes(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): number {
  const fields = {
    ...captureFields(input, streamId),
    upload_started_at: uploadStartedAt,
    image_width: input.frame.image.width,
    image_height: input.frame.image.height,
    original_bytes: input.frame.image.originalBytes,
    processed_bytes: input.frame.image.processedBytes
  };
  const encoder = new TextEncoder();
  const fieldBytes = Object.entries(fields).reduce((total, [key, value]) => {
    if (value === undefined) return total;
    return total + encoder.encode(`${key}${String(value)}`).length + 96;
  }, 0);
  return (input.frame.image.processedBytes ?? 0) + fieldBytes + 256;
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
      const uploadStartedAt = Date.now();
      const useMultipart = appConfig.analysisUploadMode === "multipart" && Boolean(input.frame.image.uri);
      const body = useMultipart
        ? multipartRequestBody(input, this.streamId, uploadStartedAt)
        : await jsonRequestBody(input, this.streamId, uploadStartedAt);
      const response = await fetch(this.endpoint, {
        method: "POST",
        ...(useMultipart ? {} : { headers: { "Content-Type": "application/json" } }),
        body,
        signal: controller.signal
      });
      const responseReceivedAt = Date.now();
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
      const guidance = parseGuidanceJson(text);
      const capture = input.frame.capture;
      const payloadBytes = input.frame.image.processedBytes ?? Math.ceil((input.frame.image.base64?.length ?? 0) * 0.75);
      const requestBodyBytes = useMultipart
        ? estimateMultipartBodyBytes(input, this.streamId, uploadStartedAt)
        : typeof body === "string" ? new TextEncoder().encode(body).length : payloadBytes;
      guidance.coordinateContext = {
        imageWidth: input.frame.image.width,
        imageHeight: input.frame.image.height,
        previewWidth: capture?.previewWidth || input.frame.image.width,
        previewHeight: capture?.previewHeight || input.frame.image.height,
        cameraFacing: capture?.cameraFacing ?? "unknown",
        imageMirrored: capture?.imageMirrored ?? false,
        previewMirrored: capture?.previewMirrored ?? false,
        resizeMode: "cover"
      };
      const networkAndServerMs = responseReceivedAt - uploadStartedAt;
      guidance.clientTiming = {
        ...(capture?.tapTimestamp !== undefined
          ? { tapTimestamp: capture.tapTimestamp }
          : {}),
        captureMs: capture ? capture.captureCompletedAt - capture.captureStartedAt : 0,
        preprocessMs: capture ? capture.preprocessCompletedAt - capture.captureCompletedAt : 0,
        payloadBytes,
        requestBodyBytes,
        uploadStartedAt,
        responseReceivedAt,
        networkAndServerMs,
        clientNetworkOverheadMs: Math.max(0, networkAndServerMs - guidance.timing.totalMs)
      };
      return {
        guidance,
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
