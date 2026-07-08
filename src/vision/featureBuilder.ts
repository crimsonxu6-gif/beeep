import { CapturedFrame } from "@/types/frame";
import { VisionFeatures } from "@/types/vision";
import { detectMockFace } from "./faceDetector";
import { detectMockPose } from "./poseDetector";

export function buildMockVisionFeatures(frame: CapturedFrame, startedAt = Date.now()): VisionFeatures {
  const face = detectMockFace(frame);
  const people = detectMockPose(frame, face);
  const phase = frame.frameId % 12;

  return {
    frameId: frame.frameId,
    imageSize: {
      width: frame.image.width,
      height: frame.image.height
    },
    people,
    face: {
      position: face.position,
      size: face.size
    },
    scene: {
      brightness: face.brightness,
      clutter: phase === 11 ? "medium" : "low"
    },
    preprocessingLatencyMs: Date.now() - startedAt
  };
}
