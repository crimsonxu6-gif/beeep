import { RefObject, useEffect, useRef } from "react";
import { CameraCapturedPicture, CameraView } from "expo-camera";

import { CapturedFrame, FrameImage } from "@/types/frame";
import { FrameSampler } from "./frameSampler";

interface UseCameraFrameSamplerOptions {
  cameraRef: RefObject<CameraView | null>;
  enabled: boolean;
  fps: number;
  onFrame: (frame: CapturedFrame) => void;
  onError?: (error: Error) => void;
}

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

export function useCameraFrameSampler({
  cameraRef,
  enabled,
  fps,
  onFrame,
  onError
}: UseCameraFrameSamplerOptions): void {
  const frameIdRef = useRef(1);
  const samplerRef = useRef(new FrameSampler(fps));
  const inFlightRef = useRef(false);
  const onFrameRef = useRef(onFrame);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    samplerRef.current = new FrameSampler(fps);
  }, [fps]);

  useEffect(() => {
    onFrameRef.current = onFrame;
    onErrorRef.current = onError;
  }, [onFrame, onError]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const intervalMs = Math.max(100, Math.floor(1000 / fps));
    const timer = setInterval(() => {
      if (inFlightRef.current || !samplerRef.current.shouldSample()) {
        return;
      }

      const camera = cameraRef.current;
      if (!camera) {
        return;
      }

      inFlightRef.current = true;
      void camera
        .takePictureAsync({
          base64: true,
          quality: 0.35,
          skipProcessing: true
        })
        .then((picture) => {
          if (!picture) {
            return;
          }

          const frame = frameFromPicture(frameIdRef.current, picture);
          if (!frame) {
            return;
          }

          frameIdRef.current += 1;
          onFrameRef.current(frame);
        })
        .catch((error: unknown) => {
          onErrorRef.current?.(error instanceof Error ? error : new Error(String(error)));
        })
        .finally(() => {
          inFlightRef.current = false;
        });
    }, intervalMs);

    return () => {
      clearInterval(timer);
    };
  }, [cameraRef, enabled, fps]);
}
