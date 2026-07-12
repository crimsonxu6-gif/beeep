import { GuidanceAction, GuidanceOutput } from "@/types/guidance";

export interface GuidanceInstructions {
  primary: string;
  secondary: string | null;
}

function clampInstruction(value: string): string {
  return Array.from(value).slice(0, 16).join("");
}

function fallbackMessage(action: GuidanceAction): string {
  if (action.type === "move_camera") {
    return {
      left: "往左一点",
      right: "往右一点",
      up: "抬高一点",
      down: "压低一点",
      forward: "靠近一点",
      back: "后退一点",
      hold: "保持角度"
    }[action.direction];
  }

  if (action.type === "adjust_pose") {
    return "姿势微调";
  }

  if (action.type === "adjust_distance") {
    return action.direction === "closer" ? "靠近一点" : "后退一点";
  }

  if (action.type === "adjust_angle") {
    return {
      lower: "手机低一点",
      raise: "手机高一点",
      tilt_left: "左倾一点",
      tilt_right: "右倾一点",
      straighten: "摆正手机"
    }[action.direction];
  }

  if (action.type === "lighting_hint") {
    return "调整光线";
  }

  if (action.type === "hold") {
    return "保持角度";
  }

  return "调整构图";
}

function primaryAction(guidance: GuidanceOutput): GuidanceAction | undefined {
  return guidance.actions[0];
}

export function guidanceToInstructions(
  guidance: GuidanceOutput | null | undefined
): GuidanceInstructions {
  const primary = guidance ? primaryAction(guidance) : undefined;
  const secondary = guidance?.actions[1];
  return {
    primary: primary ? clampInstruction(primary.message || fallbackMessage(primary)) : "",
    secondary: secondary
      ? clampInstruction(secondary.message || fallbackMessage(secondary))
      : null
  };
}

export function guidanceToInstruction(guidance: GuidanceOutput | null | undefined): string {
  return guidanceToInstructions(guidance).primary;
}
