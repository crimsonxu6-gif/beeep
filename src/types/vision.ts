export type SceneBrightness = "normal" | "low_light" | "backlight" | "overexposed";
export type SceneClutter = "low" | "medium" | "high";
export type FacePosition = "left" | "center" | "right" | "unknown";
export type FaceSize = "small" | "medium" | "large" | "unknown";

export interface PoseKeypoint {
  name: string;
  x: number;
  y: number;
  score?: number;
}

export interface PersonDetection {
  id: string;
  bbox: [number, number, number, number];
  keypoints: PoseKeypoint[];
  score: number;
}

export interface VisionFeatures {
  frameId: number;
  imageSize: {
    width: number;
    height: number;
  };
  people: PersonDetection[];
  face: {
    position: FacePosition;
    size: FaceSize;
  };
  scene: {
    brightness: SceneBrightness;
    clutter: SceneClutter;
  };
  preprocessingLatencyMs: number;
}
