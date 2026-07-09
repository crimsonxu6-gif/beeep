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
  let summary = "主体偏移";

  if (features.scene.brightness === "backlight") {
    return {
      frameId: features.frameId,
      priority: "lighting",
      actions: [
        {
          type: "lighting_hint",
          message: "转向光源",
          confidence: 0.82
        }
      ],
      summary: "人物逆光",
      confidence: 0.82
    };
  }

  if (direction !== "hold") {
    actions.push({
      type: "move_camera",
      direction,
      message: moveMessage(direction),
      confidence: 0.78
    });
  }

  if (features.face.size === "small" && actions.length < 2) {
    actions.push({
      type: "move_camera",
      direction: "forward",
      message: "靠近一点",
      confidence: 0.74
    });
    summary = "人物太小";
  }

  if (actions.length === 0) {
    priority = "hold";
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
    actions: actions.slice(0, 2),
    summary,
    confidence: 0.78
  };
}
