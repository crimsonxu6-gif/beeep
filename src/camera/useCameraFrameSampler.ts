import { RefObject, useCallback, useEffect, useRef } from "react";
import { CameraView } from "expo-camera";

import { CapturedFrame } from "@/types/frame";
import { AnalysisFrameController } from "./AnalysisFrameController";
import { AnalysisCaptureContext } from "./AnalysisFrameController";
import { FrameSampler } from "./FrameSampler";

interface UseCameraFrameSamplerOptions {
  cameraRef: RefObject<CameraView | null>;
  enabled: boolean;
  fps: number;
  onFrame: (frame: CapturedFrame) => void;
  onError?: (error: Error) => void;
  captureContext?: Omit<AnalysisCaptureContext, "tapTimestamp">;
}

export interface CameraFrameSamplerControls {
  captureNow: (tapTimestamp?: number) => Promise<boolean>;
}

export function useCameraFrameSampler({
  cameraRef,
  enabled,
  fps,
  onFrame,
  onError,
  captureContext
}: UseCameraFrameSamplerOptions): CameraFrameSamplerControls {
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

  const captureNow = useCallback(async (tapTimestamp?: number): Promise<boolean> => {
    if (inFlightRef.current) {
      return false;
    }
    const camera = cameraRef.current;
    if (!camera) {
      return false;
    }
    inFlightRef.current = true;
    try {
      const frame = await controllerRef.current.captureAnalysisFrame(
        camera,
        frameIdRef.current,
        {
          ...captureContext,
          ...(tapTimestamp !== undefined ? { tapTimestamp } : {})
        }
      );
      if (!frame) {
        return false;
      }
      frameIdRef.current += 1;
      onFrameRef.current(frame);
      return true;
    } catch (error) {
      onErrorRef.current?.(error instanceof Error ? error : new Error(String(error)));
      return false;
    } finally {
      inFlightRef.current = false;
    }
  }, [cameraRef, captureContext]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const intervalMs = Math.max(100, Math.floor(1000 / fps));
    const timer = setInterval(() => {
      if (inFlightRef.current || !samplerRef.current.shouldSample()) {
        return;
      }

      void captureNow();
    }, intervalMs);

    return () => {
      clearInterval(timer);
    };
  }, [captureNow, enabled, fps]);

  return { captureNow };
}
