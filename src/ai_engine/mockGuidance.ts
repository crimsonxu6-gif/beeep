import { GuidanceOutput, MoveDirection } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";

function directionFromSubject(features: VisionFeatures): MoveDirection {
  const subject = features.people[0];
  if (!subject) {
    return "hold";
  }

  const [x, , width] = subject.bbox;
  const centerRatio = (x + width / 2) / features.imageSize.width;

  if (centerRatio < 0.43) {
    return "left";
  }
  if (centerRatio > 0.57) {
    return "right";
  }

  return "hold";
}

function moveMessage(direction: MoveDirection): string {
  return {
    left: "往左一点",
    right: "往右一点",
    up: "抬高一点",
    down: "压低一点",
    forward: "靠近一点",
    back: "后退一点",
    hold: "保持角度"
  }[direction];
}

export function createMockGuidance(features: VisionFeatures): GuidanceOutput {
  const direction = directionFromSubject(features);
  const actions: GuidanceOutput["actions"] = [];
  let priority: GuidanceOutput["priority"] = "composition";
  let problem: GuidanceOutput["problem"] = {
    type: "subject_position",
    description: "主体偏移"
  };
  let reason = "主体中心偏离画面中线";
  let summary = "主体偏移";

  if (features.scene.brightness === "backlight") {
    return {
      frameId: features.frameId,
      priority: "lighting",
      problem: {
        type: "backlight",
        description: "人物逆光"
      },
      actions: [
        {
          type: "lighting_hint",
          message: "转向光源",
          confidence: 0.82
        }
      ],
      message: "转向光源",
      reason: "背景亮度高于人脸区域",
      summary: "人物逆光",
      confidence: 0.82
    };
  }

  if (direction !== "hold" && direction !== "forward" && direction !== "back") {
    actions.push({
      type: "move_camera",
      direction,
      message: moveMessage(direction),
      confidence: 0.78
    });
  }

  if (features.face.size === "small" && actions.length < 2) {
    priority = "distance";
    problem = {
      type: "subject_too_small",
      description: "人物太小"
    };
    reason = "人脸占画面比例偏小";
    summary = "人物太小";
    actions.push({
      type: "adjust_distance",
      direction: "closer",
      message: "靠近一点",
      confidence: 0.74
    });
  }

  if (actions.length === 0) {
    priority = "hold";
    problem = {
      type: "none",
      description: "画面稳定"
    };
    reason = "没有明显构图或光线问题";
    summary = "画面稳定";
    actions.push({
      type: "hold",
      message: "保持角度",
      confidence: 0.82
    });
  }

  return {
    frameId: features.frameId,
    priority,
    problem,
    actions: actions.slice(0, 2),
    message: actions[0]?.message ?? "保持角度",
    reason,
    summary,
    confidence: 0.78
  };
}
