import { useCallback, useEffect, useMemo, useState } from "react";

import { appConfig } from "@/config";
import { GuidancePipeline } from "@/ai_engine/guidancePipeline";
import { ShutterMuseHttpClient } from "@/ai_engine/inferenceClient";
import { StabilityFilter } from "@/stability/stabilityFilter";
import { VisionSmoother } from "@/stability/smoothing";
import { CapturedFrame } from "@/types/frame";
import { StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { MediaPipeVisionPreprocessor } from "@/vision/preprocessing";

interface GuidanceControllerState {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  latencyMs: number | null;
  processing: boolean;
  error: string | null;
}

function deriveVisionEndpoint(guidanceEndpoint: string | undefined): string | undefined {
  const trimmed = guidanceEndpoint?.trim();
  if (!trimmed) {
    return undefined;
  }

  return trimmed.endsWith("/guidance")
    ? trimmed.replace(/\/guidance$/, "/vision/features")
    : undefined;
}

export function useGuidanceController(): GuidanceControllerState & {
  handleFrame: (frame: CapturedFrame) => void;
} {
  const [stableGuidance, setStableGuidance] = useState<StableGuidance | null>(null);
  const [visionFeatures, setVisionFeatures] = useState<VisionFeatures | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pipeline = useMemo(
    () =>
      new GuidancePipeline({
        preprocessor: new MediaPipeVisionPreprocessor({
          endpoint: appConfig.mediaPipeVisionApiUrl ?? deriveVisionEndpoint(appConfig.shutterMuseApiUrl),
          timeoutMs: appConfig.aiTimeoutMs
        }),
        client: new ShutterMuseHttpClient({
          endpoint: appConfig.shutterMuseApiUrl,
          batchEndpoint: appConfig.shutterMuseBatchApiUrl,
          timeoutMs: appConfig.aiTimeoutMs
        }),
        stabilityFilter: new StabilityFilter(appConfig.stability),
        visionSmoother: new VisionSmoother(0.35),
        batchSize: appConfig.pipeline.batchSize,
        maxBatchDelayMs: appConfig.pipeline.maxBatchDelayMs,
        maxQueueSize: appConfig.pipeline.maxQueueSize
      }),
    []
  );

  useEffect(() => {
    pipeline.setCallbacks({
      onVisionFeatures: setVisionFeatures,
      onStableGuidance: setStableGuidance,
      onLatency: setLatencyMs,
      onProcessingChange: setProcessing,
      onError: (pipelineError) => setError(pipelineError.message)
    });

    return () => {
      pipeline.dispose();
    };
  }, [pipeline]);

  const handleFrame = useCallback(
    (frame: CapturedFrame) => {
      setError(null);
      void pipeline.acceptFrame(frame);
    },
    [pipeline]
  );

  return {
    stableGuidance,
    visionFeatures,
    latencyMs,
    processing,
    error,
    handleFrame
  };
}
