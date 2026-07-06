export type GuidanceActionType = "move_camera" | "adjust_pose" | "framing_hint";
export type MoveDirection = "left" | "right" | "up" | "down" | "forward" | "back" | "hold";
export type ActionStrength = "low" | "medium" | "high";

export interface MoveCameraAction {
  type: "move_camera";
  direction: MoveDirection;
  strength: ActionStrength;
}

export interface AdjustPoseAction {
  type: "adjust_pose";
  instruction: string;
  strength?: ActionStrength;
}

export interface FramingHintAction {
  type: "framing_hint";
  instruction: string;
  direction?: MoveDirection;
  strength?: ActionStrength;
}

export type GuidanceAction = MoveCameraAction | AdjustPoseAction | FramingHintAction;

export interface GuidanceOutput {
  frameId?: number;
  actions: GuidanceAction[];
  summary: string;
  confidence: number;
}

export interface StableGuidance {
  key: string;
  guidance: GuidanceOutput;
  updatedAt: number;
}
