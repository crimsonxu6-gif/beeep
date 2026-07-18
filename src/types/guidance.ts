export type GuidanceActionType =
  | "move_camera"
  | "adjust_pose"
  | "framing_hint"
  | "lighting_hint"
  | "adjust_distance"
  | "adjust_angle"
  | "hold";
export type GuidancePriority = "subject" | "lighting" | "composition" | "pose" | "camera" | "distance" | "angle" | "hold";
export type MoveDirection = "left" | "right" | "up" | "down" | "forward" | "back" | "hold";
export type AngleDirection = "lower" | "raise" | "tilt_left" | "tilt_right" | "straighten";
export type DistanceDirection = "closer" | "farther";
export type ActionStrength = "low" | "medium" | "high";
export type CompositionMode =
  | "auto"
  | "center"
  | "thirds_left"
  | "thirds_right"
  | "portrait_closeup"
  | "full_body";

export interface GuidanceProblem {
  type: string;
  description: string;
}

export interface GuidanceActionBase {
  message: string;
  confidence?: number;
  strength?: ActionStrength;
}

export interface MoveCameraAction extends GuidanceActionBase {
  type: "move_camera";
  direction: Exclude<MoveDirection, "forward" | "back" | "hold">;
}

export interface AdjustDistanceAction extends GuidanceActionBase {
  type: "adjust_distance";
  direction: DistanceDirection;
}

export interface AdjustAngleAction extends GuidanceActionBase {
  type: "adjust_angle";
  direction: AngleDirection;
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
  | AdjustDistanceAction
  | AdjustAngleAction
  | AdjustPoseAction
  | FramingHintAction
  | LightingHintAction
  | HoldAction;

export interface GuidanceOutput {
  requestId: string;
  frameId: number;
  status: "success";
  guidanceEngine?: string;
  priority?: GuidancePriority;
  problem?: GuidanceProblem;
  reason?: string;
  message?: string;
  actions: GuidanceAction[];
  summary: string;
  confidence: number;
  composition?: {
    decision: "keep" | "refine" | "reject";
    bboxNorm: [number, number, number, number];
  };
  coordinateContext?: {
    imageWidth: number;
    imageHeight: number;
    previewWidth: number;
    previewHeight: number;
    cameraFacing: "front" | "back" | "unknown";
    imageMirrored: boolean;
    previewMirrored: boolean;
    deviceOrientation?: "portrait" | "portrait_upside_down" | "landscape_left" | "landscape_right" | "unknown";
    resizeMode: "cover";
  };
  pose?: {
    keypoints: Array<{
      name: string;
      x: number;
      y: number;
      visibility: number;
    }>;
    keypointCount: 17;
  };
  subjectPreflight?: {
    state: "confirmed" | "uncertain" | "missing";
    detected: boolean;
    allowShutterMuse: boolean;
    confidence: number;
    bboxNorm?: [number, number, number, number];
    faceDetected: boolean;
    poseDetected: boolean;
    detectionSource: "face" | "pose" | "history" | "none";
    faceConfidence: number;
    poseConfidence: number;
    visiblePoseKeypoints: number;
    consecutiveMissing: number;
    consecutiveUncertain: number;
    lastConfirmedAgeMs?: number;
    historyUsed: boolean;
    blockingEnabled: boolean;
    blockedModelCall: boolean;
    reason?: string;
    reasonCode: string;
  };
  timing: {
    preflightMs?: number;
    visionMs: number;
    guidanceMs: number;
    totalMs: number;
  };
  clientTiming?: {
    tapTimestamp?: number;
    captureMs: number;
    preprocessMs: number;
    payloadBytes: number;
    estimatedRequestBodyBytes: number;
    uploadStartedAt: number;
    responseReceivedAt: number;
    overlayRenderedAt?: number;
    networkAndServerMs: number;
    clientNetworkOverheadMs: number;
    renderMs?: number;
    tapToOverlayMs?: number;
    httpStatus: number;
    uploadMode: "multipart" | "base64_json";
    apiMode: "live" | "live_debug" | "mock_success" | "mock_error" | "mock_timeout";
    captureSource: "camera" | "fixture" | "gallery";
    sourceWidth: number;
    sourceHeight: number;
    processedWidth: number;
    processedHeight: number;
    sourceBytes: number;
    processedImageBytes: number;
  };
}

export interface ModelStatus {
  code: string;
  message: string;
  suggestion: string;
  retryable: boolean;
  severity: "waiting" | "error";
}

export interface StableGuidance {
  key: string;
  guidance: GuidanceOutput;
  updatedAt: number;
}
