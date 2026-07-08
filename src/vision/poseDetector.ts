import { CapturedFrame } from "@/types/frame";
import { PersonDetection, PoseKeypoint } from "@/types/vision";
import { MockFaceDetection } from "./faceDetector";

function buildKeypoints(
  bboxLeft: number,
  bboxTop: number,
  bboxWidth: number,
  bboxHeight: number
): PoseKeypoint[] {
  return [
    {
      name: "left_shoulder",
      x: bboxLeft + bboxWidth * 0.34,
      y: bboxTop + bboxHeight * 0.3,
      score: 0.72
    },
    {
      name: "right_shoulder",
      x: bboxLeft + bboxWidth * 0.66,
      y: bboxTop + bboxHeight * 0.3,
      score: 0.72
    },
    {
      name: "nose",
      x: bboxLeft + bboxWidth * 0.5,
      y: bboxTop + bboxHeight * 0.14,
      score: 0.7
    }
  ];
}

export function detectMockPose(frame: CapturedFrame, face: MockFaceDetection): PersonDetection[] {
  const { width, height } = frame.image;
  const bboxWidth = width * 0.46;
  const bboxHeight = height * 0.58;
  const bboxLeft = Math.max(0, Math.min(width - bboxWidth, face.centerX - bboxWidth / 2));
  const bboxTop = height * 0.24;

  return [
    {
      id: "primary",
      bbox: [bboxLeft, bboxTop, bboxWidth, bboxHeight],
      score: 0.78,
      keypoints: buildKeypoints(bboxLeft, bboxTop, bboxWidth, bboxHeight)
    }
  ];
}
