import { RefObject, useCallback, useRef, useState } from "react";
import { CameraView } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import * as MediaLibrary from "expo-media-library";

import { FinalPhotoController } from "@/camera/FinalPhotoController";
import { CapturedPhoto } from "@/types/photo";

export function useCaptureController(cameraRef: RefObject<CameraView | null>) {
  const controllerRef = useRef(new FinalPhotoController());
  const [photo, setPhoto] = useState<CapturedPhoto | null>(null);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const capture = useCallback(async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);
    setError(null);
    try {
      setPhoto(await controllerRef.current.captureFinalPhoto(cameraRef.current));
    } catch {
      setError("拍照失败");
    } finally {
      setCapturing(false);
    }
  }, [cameraRef, capturing]);

  const pick = useCallback(async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError("需要图库权限");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 1,
      allowsEditing: false
    });
    const asset = result.assets?.[0];
    if (!result.canceled && asset) {
      setPhoto({ uri: asset.uri, width: asset.width, height: asset.height, source: "library" });
    }
  }, []);

  const save = useCallback(async () => {
    if (!photo) return false;
    const permission = await MediaLibrary.requestPermissionsAsync();
    if (!permission.granted) {
      setError("需要相册权限");
      return false;
    }
    await MediaLibrary.saveToLibraryAsync(photo.uri);
    return true;
  }, [photo]);

  const clear = useCallback(() => setPhoto(null), []);
  return { photo, capturing, error, capture, pick, save, clear };
}
