export interface FrameImage {
  base64?: string;
  uri?: string;
  width: number;
  height: number;
  mimeType: "image/jpeg" | string;
}

export interface CapturedFrame {
  frameId: number;
  timestamp: number;
  image: FrameImage;
}
