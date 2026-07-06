import { CapturedFrame } from "@/types/frame";
import { GuidanceOutput } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { buildGuidancePrompt, guidanceJsonSchema } from "./promptManager";
import { parseGuidanceJson } from "./jsonParser";
import { createMockGuidance } from "./mockGuidance";

export interface GuidanceEngineInput {
  frame: CapturedFrame;
  visionFeatures: VisionFeatures;
}

export interface GuidanceInferenceClient {
  infer(input: GuidanceEngineInput): Promise<GuidanceOutput>;
  inferBatch(inputs: GuidanceEngineInput[]): Promise<GuidanceOutput[]>;
}

interface ShutterMuseHttpClientOptions {
  endpoint: string | undefined;
  batchEndpoint: string | undefined;
  timeoutMs: number;
}

function endpointOrUndefined(value?: string): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...init,
      signal: controller.signal
    });
  } finally {
    clearTimeout(timer);
  }
}

function serializeInput(input: GuidanceEngineInput, retryReason?: string): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    frame_id: input.frame.frameId,
    timestamp: input.frame.timestamp,
    image: {
      base64: input.frame.image.base64,
      uri: input.frame.image.uri,
      width: input.frame.image.width,
      height: input.frame.image.height,
      mime_type: input.frame.image.mimeType
    },
    vision_features: input.visionFeatures,
    prompt: buildGuidancePrompt(input.visionFeatures),
    schema: guidanceJsonSchema
  };

  if (retryReason) {
    payload.retry = { reason: retryReason };
  }

  return payload;
}

async function parseHttpResponse(response: Response): Promise<GuidanceOutput> {
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`ShutterMuse API failed with HTTP ${response.status}: ${text.slice(0, 160)}`);
  }

  return parseGuidanceJson(text);
}

export class ShutterMuseHttpClient implements GuidanceInferenceClient {
  private readonly endpoint: string | undefined;
  private readonly batchEndpoint: string | undefined;
  private readonly timeoutMs: number;

  constructor(options: ShutterMuseHttpClientOptions) {
    this.endpoint = endpointOrUndefined(options.endpoint);
    this.batchEndpoint = endpointOrUndefined(options.batchEndpoint);
    this.timeoutMs = options.timeoutMs;
  }

  async infer(input: GuidanceEngineInput): Promise<GuidanceOutput> {
    if (!this.endpoint) {
      return createMockGuidance(input.visionFeatures);
    }

    let retryReason: string | undefined;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const response = await fetchWithTimeout(
        this.endpoint,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(serializeInput(input, retryReason))
        },
        this.timeoutMs
      );

      try {
        return await parseHttpResponse(response);
      } catch (error) {
        retryReason = error instanceof Error ? error.message : String(error);
        if (attempt === 1) {
          throw error;
        }
      }
    }

    return createMockGuidance(input.visionFeatures);
  }

  async inferBatch(inputs: GuidanceEngineInput[]): Promise<GuidanceOutput[]> {
    if (inputs.length === 0) {
      return [];
    }

    if (!this.endpoint) {
      return inputs.map((input) => createMockGuidance(input.visionFeatures));
    }

    if (this.batchEndpoint && inputs.length > 1) {
      const response = await fetchWithTimeout(
        this.batchEndpoint,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            requests: inputs.map((input) => serializeInput(input))
          })
        },
        this.timeoutMs
      );

      const text = await response.text();
      if (!response.ok) {
        throw new Error(`ShutterMuse batch API failed with HTTP ${response.status}: ${text.slice(0, 160)}`);
      }

      const parsed = JSON.parse(text) as unknown;
      if (!Array.isArray(parsed)) {
        throw new Error("ShutterMuse batch API must return a JSON array.");
      }

      return parsed.map((item) => parseGuidanceJson(JSON.stringify(item)));
    }

    return Promise.all(inputs.map((input) => this.infer(input)));
  }
}
