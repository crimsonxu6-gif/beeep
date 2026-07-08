import { CapturedFrame } from "@/types/frame";
import { FacePosition, FaceSize, SceneBrightness } from "@/types/vision";

export interface MockFaceDetection {
  centerX: number;
  centerY: number;
  position: FacePosition;
  size: FaceSize;
  brightness: SceneBrightness;
}

function classifyFacePosition(centerX: number, width: number): FacePosition {
  const ratio = centerX / width;
  if (ratio < 0.42) {
    return "left";
  }
  if (ratio > 0.58) {
    return "right";
  }
  return "center";
}

function classifyFaceSize(faceHeight: number, imageHeight: number): FaceSize {
  const ratio = faceHeight / imageHeight;
  if (ratio < 0.36) {
    return "small";
  }
  if (ratio > 0.68) {
    return "large";
  }
  return "medium";
}

export function detectMockFace(frame: CapturedFrame): MockFaceDetection {
  const { width, height } = frame.image;
  const phase = frame.frameId % 12;
  const horizontalOffset = phase < 4 ? -0.13 : phase < 8 ? 0.14 : 0;
  const centerX = width * (0.5 + horizontalOffset);
  const faceHeight = height * 0.58;

  return {
    centerX,
    centerY: height * 0.36,
    position: classifyFacePosition(centerX, width),
    size: classifyFaceSize(faceHeight, height),
    brightness: phase === 10 ? "backlight" : "normal"
  };
}
