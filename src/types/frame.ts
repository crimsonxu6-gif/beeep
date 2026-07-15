export interface FrameImage {
  base64?: string;
  uri?: string;
  width: number;
  height: number;
  mimeType: "image/jpeg" | string;
  originalBytes?: number;
  processedBytes?: number;
}

export type CameraFacing = "front" | "back" | "unknown";
export type DeviceOrientation =
  | "portrait"
  | "portrait_upside_down"
  | "landscape_left"
  | "landscape_right"
  | "unknown";

export interface FrameCaptureMetadata {
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
}

export interface CapturedFrame {
  frameId: number;
  timestamp: number;
  image: FrameImage;
  capture?: FrameCaptureMetadata;
}
