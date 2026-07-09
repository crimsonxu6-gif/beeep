export type GuidanceActionType = "move_camera" | "adjust_pose" | "framing_hint" | "lighting_hint" | "hold";
export type GuidancePriority = "subject" | "lighting" | "composition" | "pose" | "camera" | "hold";
export type MoveDirection = "left" | "right" | "up" | "down" | "forward" | "back" | "hold";
export type ActionStrength = "low" | "medium" | "high";

export interface GuidanceActionBase {
  message: string;
  confidence?: number;
  strength?: ActionStrength;
}

export interface MoveCameraAction extends GuidanceActionBase {
  type: "move_camera";
  direction: MoveDirection;
}

export interface AdjustPoseAction extends GuidanceActionBase {
  type: "adjust_pose";
  instruction?: string;
}

export interface FramingHintAction extends GuidanceActionBase {
  type: "framing_hint";
  direction?: MoveDirection;
  instruction?: string;
}

export interface LightingHintAction extends GuidanceActionBase {
  type: "lighting_hint";
  instruction?: string;
}

export interface HoldAction extends GuidanceActionBase {
  type: "hold";
}

export type GuidanceAction =
  | MoveCameraAction
  | AdjustPoseAction
  | FramingHintAction
  | LightingHintAction
  | HoldAction;

export interface GuidanceOutput {
  frameId?: number;
  priority?: GuidancePriority;
  actions: GuidanceAction[];
  summary: string;
  confidence: number;
}

export interface StableGuidance {
  key: string;
  guidance: GuidanceOutput;
  updatedAt: number;
}
