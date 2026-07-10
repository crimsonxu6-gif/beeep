import { RefObject, useEffect, useRef } from "react";
import { CameraView } from "expo-camera";

import { CapturedFrame } from "@/types/frame";
import { AnalysisFrameController } from "./AnalysisFrameController";
import { FrameSampler } from "./FrameSampler";

interface UseCameraFrameSamplerOptions {
  cameraRef: RefObject<CameraView | null>;
  enabled: boolean;
  fps: number;
  onFrame: (frame: CapturedFrame) => void;
  onError?: (error: Error) => void;
}

export function useCameraFrameSampler({
  cameraRef,
  enabled,
  fps,
  onFrame,
  onError
}: UseCameraFrameSamplerOptions): void {
  const frameIdRef = useRef(1);
  const controllerRef = useRef(new AnalysisFrameController());
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
      void controllerRef.current
        .captureAnalysisFrame(camera, frameIdRef.current)
        .then((frame) => {
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
