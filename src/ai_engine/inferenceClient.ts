import {
  AnalysisApiMode,
  AnalysisFailureScenario,
  AnalysisUploadMode,
  CapturedFrame,
  SimulatedNetworkProfile
} from "@/types/frame";
import { CompositionMode, GuidanceOutput, ModelStatus } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { GuidanceParseError, parseGuidanceJson } from "./jsonParser";
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

export interface ShutterMuseHttpClientOptions {
  endpoint: string | undefined;
  debugEndpoint?: string;
  timeoutMs: number;
  mockEnabled: boolean;
  apiMode?: AnalysisApiMode;
  uploadMode?: AnalysisUploadMode;
  networkProfile?: SimulatedNetworkProfile;
  failureScenario?: AnalysisFailureScenario;
}

function abortError(): Error {
  const error = new Error("Aborted");
  error.name = "AbortError";
  return error;
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(abortError());
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(abortError());
    }, { once: true });
  });
}

function endpointOrUndefined(value?: string): string | undefined {
  const trimmed = value?.trim();
  if (!trimmed) return undefined;
  if (trimmed.endsWith("/guidance")) return trimmed.replace(/\/guidance$/, "/v1/analyze");
  return trimmed;
}

function debugEndpointForScenario(endpoint: string, scenario: AnalysisFailureScenario): string {
  const separator = endpoint.includes("?") ? "&" : "?";
  return `${endpoint}${separator}scenario=${encodeURIComponent(scenario)}`;
}

export function captureFields(input: GuidanceEngineInput, streamId: string): Record<string, unknown> {
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
      processed_bytes: input.frame.image.processedImageBytes
    }
  });
}

export function multipartMetadata(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): Record<string, unknown> {
  return {
    ...captureFields(input, streamId),
    upload_mode: "multipart",
    upload_started_at: uploadStartedAt,
    image_width: input.frame.image.width,
    image_height: input.frame.image.height,
    original_bytes: input.frame.image.originalBytes,
    processed_bytes: input.frame.image.processedImageBytes
  };
}

export function multipartImagePart(input: GuidanceEngineInput): {
  uri: string;
  name: string;
  type: string;
} {
  if (!input.frame.image.uri) throw new Error("Analysis image URI is missing");
  return {
    uri: input.frame.image.uri,
    name: `analysis-${input.frame.frameId}.jpg`,
    type: input.frame.image.mimeType
  };
}

export async function multipartRequestBody(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): Promise<FormData> {
  const form = new FormData();
  const fields = multipartMetadata(input, streamId, uploadStartedAt);
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined) form.append(key, String(value));
  }
  const part = multipartImagePart(input);
  const { File } = await import("expo-file-system");
  form.append("image", new File(part.uri), part.name);
  return form;
}

function mockSuccess(
  input: GuidanceEngineInput,
  uploadMode: "multipart" | "base64_json"
): AnalyzeResult {
  const capture = input.frame.capture;
  const now = Date.now();
  return {
    guidance: {
      requestId: `mock_${input.frame.frameId}`,
      frameId: input.frame.frameId,
      status: "success",
      guidanceEngine: "fixture_mock",
      priority: "composition",
      problem: { type: "subject_position", description: "主体稍微偏右" },
      reason: "固定响应仅用于模拟器 UI 回归",
      message: "镜头稍微往左移",
      actions: [{ type: "move_camera", direction: "left", message: "镜头稍微往左移", confidence: 0.86 }],
      summary: "模拟构图建议",
      confidence: 0.86,
      composition: { decision: "refine", bboxNorm: [0.15, 0.1, 0.8, 0.9] },
      coordinateContext: {
        imageWidth: input.frame.image.width,
        imageHeight: input.frame.image.height,
        previewWidth: capture?.previewWidth || input.frame.image.width,
        previewHeight: capture?.previewHeight || input.frame.image.height,
        cameraFacing: capture?.cameraFacing ?? "unknown",
        imageMirrored: capture?.imageMirrored ?? false,
        previewMirrored: capture?.previewMirrored ?? false,
        resizeMode: "cover"
      },
      timing: { visionMs: 0, guidanceMs: 0, totalMs: 0 },
      clientTiming: buildClientTiming(input, now, now, 200, uploadMode, "mock_success")
    },
    visionFeatures: null
  };
}

function buildClientTiming(
  input: GuidanceEngineInput,
  uploadStartedAt: number,
  responseReceivedAt: number,
  httpStatus: number,
  uploadMode: "multipart" | "base64_json",
  apiMode: AnalysisApiMode,
  serverTotalMs = 0,
  estimatedRequestBodyBytes?: number
): NonNullable<GuidanceOutput["clientTiming"]> {
  const capture = input.frame.capture;
  const payloadBytes = input.frame.image.processedImageBytes
    ?? Math.ceil((input.frame.image.base64?.length ?? 0) * 0.75);
  const networkAndServerMs = responseReceivedAt - uploadStartedAt;
  return {
    ...(capture?.tapTimestamp !== undefined ? { tapTimestamp: capture.tapTimestamp } : {}),
    captureMs: capture ? capture.captureCompletedAt - capture.captureStartedAt : 0,
    preprocessMs: capture ? capture.preprocessCompletedAt - capture.captureCompletedAt : 0,
    payloadBytes,
    estimatedRequestBodyBytes: estimatedRequestBodyBytes ?? payloadBytes,
    uploadStartedAt,
    responseReceivedAt,
    networkAndServerMs,
    clientNetworkOverheadMs: Math.max(0, networkAndServerMs - serverTotalMs),
    httpStatus,
    uploadMode,
    apiMode,
    captureSource: capture?.source ?? "camera",
    sourceWidth: input.frame.image.originalWidth ?? input.frame.image.width,
    sourceHeight: input.frame.image.originalHeight ?? input.frame.image.height,
    processedWidth: input.frame.image.width,
    processedHeight: input.frame.image.height,
    sourceBytes: input.frame.image.originalBytes ?? payloadBytes,
    processedImageBytes: input.frame.image.processedImageBytes ?? payloadBytes
  };
}

function mockFailureStatus(
  scenario: AnalysisFailureScenario
): ModelStatus {
  const httpCode = scenario.startsWith("http_") ? scenario.slice(5) : null;
  if (httpCode) {
    return {
      code: `HTTP_${httpCode}`,
      message: "AI 暂时无法使用",
      suggestion: "可以稍后再试",
      retryable: true,
      severity: "error"
    };
  }
  if (scenario === "bbox_safety_rejected") {
    return {
      code: "BBOX_SAFETY_REJECTED",
      message: "这次推荐框不够稳定",
      suggestion: "稍微换个角度再分析",
      retryable: true,
      severity: "error"
    };
  }
  return {
    code: "INVALID_MODEL_OUTPUT",
    message: "这次没看懂画面",
    suggestion: scenario === "invalid_json" ? "稍微换个角度再试" : "稍微换个角度再试",
    retryable: true,
    severity: "error"
  };
}

export function estimatedMultipartRequestBodyBytes(
  input: GuidanceEngineInput,
  streamId: string,
  uploadStartedAt: number
): number {
  const fields = multipartMetadata(input, streamId, uploadStartedAt);
  const encoder = new TextEncoder();
  const fieldBytes = Object.entries(fields).reduce((total, [key, value]) => {
    if (value === undefined) return total;
    return total + encoder.encode(`${key}${String(value)}`).length + 96;
  }, 0);
  return (input.frame.image.processedImageBytes ?? 0) + fieldBytes + 256;
}

function parseVisionFeatures(value: unknown): VisionFeatures | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const features = (raw.vision_features ?? raw.visionFeatures) as VisionFeatures | undefined;
  return features ?? null;
}

export class ShutterMuseHttpClient implements GuidanceInferenceClient {
  private readonly endpoint: string | undefined;
  private readonly debugEndpoint: string | undefined;
  private readonly streamId = `camera_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;

  constructor(private readonly options: ShutterMuseHttpClientOptions) {
    this.endpoint = endpointOrUndefined(options.endpoint);
    this.debugEndpoint = endpointOrUndefined(options.debugEndpoint);
  }

  async infer(input: GuidanceEngineInput): Promise<AnalyzeResult> {
    const capture = input.frame.capture;
    const apiMode = this.options.apiMode ?? (appConfig.analysisFixtureEnabled
      ? capture?.apiMode ?? appConfig.analysisApiMode
      : appConfig.analysisApiMode);
    const uploadMode = this.options.uploadMode ?? (appConfig.analysisFixtureEnabled
      ? capture?.uploadMode ?? appConfig.analysisUploadMode
      : appConfig.analysisUploadMode);
    const networkProfile = this.options.networkProfile ?? (appConfig.analysisFixtureEnabled
      ? capture?.networkProfile ?? "normal"
      : "normal");
    const failureScenario = this.options.failureScenario
      ?? capture?.failureScenario
      ?? "invalid_model_output";
    const requestEndpoint = apiMode === "live_debug"
      ? this.debugEndpoint && debugEndpointForScenario(this.debugEndpoint, failureScenario)
      : this.endpoint;
    if (!requestEndpoint && (apiMode === "live" || apiMode === "live_debug")) {
      if (this.options.mockEnabled && apiMode === "live") {
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
      if (networkProfile === "simulated_offline_before_fetch") {
        throw new TypeError("Simulated offline network");
      }
      if (networkProfile === "simulated_pre_request_delay") {
        await wait(2500, controller.signal);
      }
      if (apiMode === "mock_timeout") {
        await wait(this.options.timeoutMs + 50, controller.signal);
      }
      if (apiMode === "mock_error") {
        throw new GuidanceApiError(mockFailureStatus(failureScenario));
      }
      if (apiMode === "mock_success") {
        return mockSuccess(input, uploadMode);
      }
      const useMultipart = uploadMode === "multipart" && Boolean(input.frame.image.uri);
      const body = useMultipart
        ? await multipartRequestBody(input, this.streamId, uploadStartedAt)
        : await jsonRequestBody(input, this.streamId, uploadStartedAt);
      const response = await fetch(requestEndpoint!, {
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
      const payloadBytes = input.frame.image.processedImageBytes ?? Math.ceil((input.frame.image.base64?.length ?? 0) * 0.75);
      const estimatedRequestBodyBytes = useMultipart
        ? estimatedMultipartRequestBodyBytes(input, this.streamId, uploadStartedAt)
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
      guidance.clientTiming = buildClientTiming(
        input,
        uploadStartedAt,
        responseReceivedAt,
        response.status,
        useMultipart ? "multipart" : "base64_json",
        apiMode,
        guidance.timing.totalMs,
        estimatedRequestBodyBytes
      );
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
      if (error instanceof GuidanceParseError || error instanceof SyntaxError) {
        throw new GuidanceApiError({
          code: "INVALID_MODEL_OUTPUT",
          message: "这次没看懂画面",
          suggestion: "稍微换个角度再试",
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
