export interface FrameImage {
  base64?: string;
  uri?: string;
  width: number;
  height: number;
  mimeType: "image/jpeg" | string;
  originalBytes?: number;
  processedBytes?: number;
  originalWidth?: number;
  originalHeight?: number;
}

export type CameraFacing = "front" | "back" | "unknown";
export type AnalysisFrameSource = "camera" | "fixture" | "gallery";
export type AnalysisApiMode = "live" | "mock_success" | "mock_error" | "mock_timeout";
export type AnalysisUploadMode = "multipart" | "base64_json";
export type SimulatedNetworkProfile = "normal" | "slow" | "offline";
export type AnalysisFailureScenario =
  | "invalid_model_output"
  | "http_500"
  | "http_502"
  | "http_503"
  | "http_504"
  | "invalid_json"
  | "missing_bbox"
  | "bbox_safety_rejected";
export type DeviceOrientation =
  | "portrait"
  | "portrait_upside_down"
  | "landscape_left"
  | "landscape_right"
  | "unknown";

export interface FrameCaptureMetadata {
  source: AnalysisFrameSource;
  tapTimestamp?: number;
  captureStartedAt: number;
  captureCompletedAt: number;
  preprocessCompletedAt: number;
  cameraFacing: CameraFacing;
  imageMirrored: boolean;
  previewMirrored: boolean;
  deviceOrientation: DeviceOrientation;
  previewWidth: number;
  previewHeight: number;
  apiMode?: AnalysisApiMode;
  uploadMode?: AnalysisUploadMode;
  networkProfile?: SimulatedNetworkProfile;
  failureScenario?: AnalysisFailureScenario;
}

export interface AnalysisSourceFrame {
  uri: string;
  width: number;
  height: number;
  cameraFacing: CameraFacing;
  imageMirrored: boolean;
  previewMirrored: boolean;
  deviceOrientation: DeviceOrientation;
  source: AnalysisFrameSource;
  captureStartedAt?: number;
  captureCompletedAt?: number;
}

export interface CapturedFrame {
  frameId: number;
  timestamp: number;
  image: FrameImage;
  capture?: FrameCaptureMetadata;
}
