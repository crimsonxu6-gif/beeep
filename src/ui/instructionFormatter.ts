import { GuidanceAction, GuidanceOutput } from "@/types/guidance";

const moveText = {
  left: "往左一点",
  right: "往右一点",
  up: "抬高一点",
  down: "压低一点",
  forward: "靠近一点",
  back: "退后一点",
  hold: "很好，保持"
} as const;

function clampInstruction(value: string): string {
  return Array.from(value).slice(0, 10).join("");
}

function poseInstruction(value: string): string {
  const text = value.toLowerCase();
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
  return value;
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

  if (action.instruction.toLowerCase().includes("backlight")) {
    return "避开逆光";
  }

  if (action.instruction.toLowerCase().includes("hold")) {
    return "很好，保持";
  }

  return action.instruction;
}

export function guidanceToInstruction(guidance: GuidanceOutput | null | undefined): string {
  const action = guidance?.actions[0];
  if (!action) {
    return "寻找主体";
  }

  return clampInstruction(actionToInstruction(action));
}
