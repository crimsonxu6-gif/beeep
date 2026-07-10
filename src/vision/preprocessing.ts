import { CapturedFrame } from "@/types/frame";
import {
  FacePosition,
  FaceSize,
  PersonDetection,
  SceneBrightness,
  SceneClutter,
  VisionFeatures
} from "@/types/vision";
import { buildMockVisionFeatures } from "./featureBuilder";
import { isMockEnabled } from "@/config";

export interface VisionPreprocessor {
  preprocess(frame: CapturedFrame): Promise<VisionFeatures>;
}

interface MediaPipeVisionPreprocessorOptions {
  endpoint: string | undefined;
  timeoutMs: number;
  fallbackToMock?: boolean;
}

function endpointOrUndefined(value?: string): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringValue<T extends string>(value: unknown, fallback: T): T {
  return typeof value === "string" ? (value as T) : fallback;
}

function boundedTuple(value: unknown): [number, number, number, number] {
  if (!Array.isArray(value)) {
    return [0, 0, 0, 0];
  }

  return [
    numberValue(value[0], 0),
    numberValue(value[1], 0),
    numberValue(value[2], 0),
    numberValue(value[3], 0)
  ];
}

function parsePeople(value: unknown): PersonDetection[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isRecord).map((person, index) => {
    const keypoints = Array.isArray(person.keypoints)
      ? person.keypoints.filter(isRecord).map((keypoint) => ({
          name: String(keypoint.name ?? "point"),
          x: numberValue(keypoint.x, 0),
          y: numberValue(keypoint.y, 0),
          score: numberValue(keypoint.score, 0)
        }))
      : [];

    return {
      id: String(person.id ?? `person-${index}`),
      bbox: boundedTuple(person.bbox),
      keypoints,
      score: numberValue(person.score, 0)
    };
  });
}

function parseVisionFeatures(rawValue: unknown, frame: CapturedFrame): VisionFeatures {
  const raw = isRecord(rawValue) && isRecord(rawValue.vision_features)
    ? rawValue.vision_features
    : rawValue;

  if (!isRecord(raw)) {
    throw new Error("MediaPipe vision response must be a JSON object.");
  }

  const imageSize = isRecord(raw.imageSize) ? raw.imageSize : raw.image_size;
  const face = isRecord(raw.face) ? raw.face : {};
  const scene = isRecord(raw.scene) ? raw.scene : {};

  return {
    frameId: numberValue(raw.frameId ?? raw.frame_id, frame.frameId),
    imageSize: {
      width: numberValue(isRecord(imageSize) ? imageSize.width : undefined, frame.image.width),
      height: numberValue(isRecord(imageSize) ? imageSize.height : undefined, frame.image.height)
    },
    people: parsePeople(raw.people),
    face: {
      position: stringValue<FacePosition>(face.position, "unknown"),
      size: stringValue<FaceSize>(face.size, "unknown")
    },
    scene: {
      brightness: stringValue<SceneBrightness>(scene.brightness, "normal"),
      clutter: stringValue<SceneClutter>(scene.clutter, "low")
    },
    preprocessingLatencyMs: numberValue(
      raw.preprocessingLatencyMs ?? raw.preprocessing_latency_ms,
      0
    )
  };
}

async function postJsonWithTimeout(
  url: string,
  body: Record<string, unknown>,
  timeoutMs: number
): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body),
      signal: controller.signal
    });
    const text = await response.text();

    if (!response.ok) {
      throw new Error(`MediaPipe vision API failed with HTTP ${response.status}: ${text.slice(0, 160)}`);
    }

    return JSON.parse(text) as unknown;
  } finally {
    clearTimeout(timer);
  }
}

function serializeFrame(frame: CapturedFrame): Record<string, unknown> {
  return {
    frame_id: frame.frameId,
    timestamp: frame.timestamp,
    image: {
      base64: frame.image.base64,
      uri: frame.image.uri,
      width: frame.image.width,
      height: frame.image.height,
      mime_type: frame.image.mimeType
    }
  };
}

export class MediaPipeVisionPreprocessor implements VisionPreprocessor {
  private readonly endpoint: string | undefined;
  private readonly timeoutMs: number;
  private readonly fallbackToMock: boolean;

  constructor(options: MediaPipeVisionPreprocessorOptions) {
    this.endpoint = endpointOrUndefined(options.endpoint);
    this.timeoutMs = options.timeoutMs;
    this.fallbackToMock =
      options.fallbackToMock === true &&
      isMockEnabled(
        typeof __DEV__ !== "undefined" && __DEV__,
        process.env.EXPO_PUBLIC_ENABLE_MOCK
      );
  }

  async preprocess(frame: CapturedFrame): Promise<VisionFeatures> {
    if (!this.endpoint) {
      return buildMockVisionFeatures(frame);
    }

    try {
      const raw = await postJsonWithTimeout(this.endpoint, serializeFrame(frame), this.timeoutMs);
      return parseVisionFeatures(raw, frame);
    } catch (error) {
      if (this.fallbackToMock) {
        return buildMockVisionFeatures(frame);
      }

      throw error;
    }
  }
}
