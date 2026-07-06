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

export function createMockGuidance(features: VisionFeatures): GuidanceOutput {
  const direction = directionFromSubject(features);
  const actions: GuidanceOutput["actions"] = [];

  if (direction !== "hold") {
    actions.push({
      type: "move_camera",
      direction,
      strength: "medium"
    });
  }

  if (features.face.size === "small") {
    actions.push({
      type: "move_camera",
      direction: "forward",
      strength: "low"
    });
  }

  if (features.scene.brightness === "backlight") {
    actions.push({
      type: "framing_hint",
      instruction: "avoid backlight",
      direction: "hold",
      strength: "medium"
    });
  }

  if (actions.length === 0) {
    actions.push({
      type: "framing_hint",
      instruction: "hold steady",
      direction: "hold",
      strength: "low"
    });
  }

  return {
    frameId: features.frameId,
    actions: actions.slice(0, 2),
    summary: direction === "hold" ? "composition is stable" : "subject is off center",
    confidence: 0.78
  };
}
