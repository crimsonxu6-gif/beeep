import { GuidanceAction, GuidanceOutput } from "@/types/guidance";

const moveText = {
  left: "往左一点",
  right: "往右一点",
  up: "抬高一点",
  down: "压低一点",
  forward: "靠近一点",
  back: "后退一点",
  hold: "很好保持"
} as const;

function clampInstruction(value: string): string {
  return Array.from(value).slice(0, 10).join("");
}

function poseInstruction(value: string): string {
  const text = value.toLowerCase();
  if (text.includes("turn") && text.includes("right")) {
    return "头右一点";
  }
  if (text.includes("turn") && text.includes("left")) {
    return "头左一点";
  }
  if (text.includes("head") && text.includes("right")) {
    return "头右一点";
  }
  if (text.includes("head") && text.includes("left")) {
    return "头左一点";
  }
  if (text.includes("chin") || text.includes("jaw")) {
    return "下巴微收";
  }
  if (text.includes("shoulder")) {
    return "肩膀放松";
  }
  if (text.includes("pose")) {
    return "姿势微调";
  }
  return value;
}

function framingInstruction(value: string): string {
  const text = value.toLowerCase();
  if (text.includes("backlight")) {
    return "避开逆光";
  }
  if (text.includes("exposure")) {
    return "提高曝光";
  }
  if (text.includes("background") || text.includes("clutter")) {
    return "背景简洁";
  }
  if (text.includes("third")) {
    return "靠近三分线";
  }
  if (text.includes("steady") || text.includes("hold")) {
    return "很好保持";
  }
  if (text.includes("subject")) {
    return "寻找主体";
  }
  return value;
}

function primaryAction(guidance: GuidanceOutput): GuidanceAction | undefined {
  return (
    guidance.actions.find((action) => action.type === "move_camera") ??
    guidance.actions.find((action) => action.type === "adjust_pose") ??
    guidance.actions.find((action) => action.type === "framing_hint")
  );
}

function actionToInstruction(action: GuidanceAction): string {
  if (action.type === "move_camera") {
    return moveText[action.direction];
  }

  if (action.type === "adjust_pose") {
    return poseInstruction(action.instruction);
  }

  if (action.direction && action.direction !== "hold") {
    return moveText[action.direction];
  }

  return framingInstruction(action.instruction);
}

export function guidanceToInstruction(guidance: GuidanceOutput | null | undefined): string {
  const action = guidance ? primaryAction(guidance) : undefined;
  if (!action) {
    return "寻找主体";
  }

  return clampInstruction(actionToInstruction(action));
}
