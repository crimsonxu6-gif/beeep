import { CameraCapturedPicture, CameraView } from "expo-camera";

import { CapturedFrame, FrameImage } from "@/types/frame";

export interface CameraControllerOptions {
  quality: number;
  includeBase64: boolean;
}

const defaultOptions: CameraControllerOptions = {
  quality: 0.28,
  includeBase64: true
};

function frameFromPicture(frameId: number, picture: CameraCapturedPicture): CapturedFrame | null {
  if (!picture.base64 && !picture.uri) {
    return null;
  }

  const image: FrameImage = {
    width: picture.width,
    height: picture.height,
    mimeType: "image/jpeg"
  };

  if (picture.base64) {
    image.base64 = picture.base64;
  }

  if (picture.uri) {
    image.uri = picture.uri;
  }

  return {
    frameId,
    timestamp: Date.now(),
    image
  };
}

export class CameraController {
  constructor(private readonly options: CameraControllerOptions = defaultOptions) {}

  async captureFrame(camera: CameraView, frameId: number): Promise<CapturedFrame | null> {
    const picture = await camera.takePictureAsync({
      base64: this.options.includeBase64,
      quality: this.options.quality,
      skipProcessing: true,
      shutterSound: false
    });

    if (!picture) {
      return null;
    }

    return frameFromPicture(frameId, picture);
  }
}
