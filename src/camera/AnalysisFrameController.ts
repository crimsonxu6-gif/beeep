import { CameraCapturedPicture, CameraView } from "expo-camera";
import { CapturedFrame, FrameImage } from "@/types/frame";

function frameFromPicture(frameId: number, picture: CameraCapturedPicture): CapturedFrame | null {
  if (!picture.base64) return null;
  const image: FrameImage = {
    base64: picture.base64,
    uri: picture.uri,
    width: picture.width,
    height: picture.height,
    mimeType: "image/jpeg"
  };
  return { frameId, timestamp: Date.now(), image };
}

export class AnalysisFrameController {
  async captureAnalysisFrame(camera: CameraView, frameId: number): Promise<CapturedFrame | null> {
    const picture = await camera.takePictureAsync({
      base64: true,
      quality: 0.28,
      skipProcessing: true,
      shutterSound: false
    });
    return picture ? frameFromPicture(frameId, picture) : null;
  }
}
