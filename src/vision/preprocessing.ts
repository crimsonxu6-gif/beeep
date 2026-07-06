import { CapturedFrame } from "@/types/frame";
import { FacePosition, FaceSize, PersonDetection, VisionFeatures } from "@/types/vision";

export interface VisionPreprocessor {
  preprocess(frame: CapturedFrame): Promise<VisionFeatures>;
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

function classifyFaceSize(bboxHeight: number, imageHeight: number): FaceSize {
  const ratio = bboxHeight / imageHeight;
  if (ratio < 0.36) {
    return "small";
  }
  if (ratio > 0.68) {
    return "large";
  }
  return "medium";
}

export class PrototypeVisionPreprocessor implements VisionPreprocessor {
  async preprocess(frame: CapturedFrame): Promise<VisionFeatures> {
    const start = Date.now();
    const { width, height } = frame.image;

    const phase = frame.frameId % 12;
    const horizontalOffset = phase < 4 ? -0.13 : phase < 8 ? 0.14 : 0;
    const bboxWidth = width * 0.46;
    const bboxHeight = height * 0.58;
    const centerX = width * (0.5 + horizontalOffset);
    const bboxLeft = Math.max(0, Math.min(width - bboxWidth, centerX - bboxWidth / 2));
    const bboxTop = height * 0.24;

    const people: PersonDetection[] = [
      {
        id: "primary",
        bbox: [bboxLeft, bboxTop, bboxWidth, bboxHeight],
        score: 0.78,
        keypoints: [
          { name: "left_shoulder", x: bboxLeft + bboxWidth * 0.34, y: bboxTop + bboxHeight * 0.3, score: 0.72 },
          { name: "right_shoulder", x: bboxLeft + bboxWidth * 0.66, y: bboxTop + bboxHeight * 0.3, score: 0.72 },
          { name: "nose", x: bboxLeft + bboxWidth * 0.5, y: bboxTop + bboxHeight * 0.14, score: 0.7 }
        ]
      }
    ];

    return {
      frameId: frame.frameId,
      imageSize: {
        width,
        height
      },
      people,
      face: {
        position: classifyFacePosition(centerX, width),
        size: classifyFaceSize(bboxHeight, height)
      },
      scene: {
        brightness: phase === 10 ? "backlight" : "normal",
        clutter: phase === 11 ? "medium" : "low"
      },
      preprocessingLatencyMs: Date.now() - start
    };
  }
}
