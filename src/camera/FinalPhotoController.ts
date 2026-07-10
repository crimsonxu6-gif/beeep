import { CameraView } from "expo-camera";
import { CapturedPhoto } from "@/types/photo";

export class FinalPhotoController {
  async captureFinalPhoto(camera: CameraView): Promise<CapturedPhoto | null> {
    const picture = await camera.takePictureAsync({
      base64: false,
      quality: 1,
      skipProcessing: false,
      shutterSound: false
    });
    if (!picture) return null;
    return { uri: picture.uri, width: picture.width, height: picture.height, source: "camera" };
  }
}
