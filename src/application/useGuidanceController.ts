import { useCallback, useEffect, useMemo, useState } from "react";

import { appConfig } from "@/config";
import { GuidanceDebugState, GuidancePipeline } from "@/ai_engine/guidancePipeline";
import { ShutterMuseHttpClient } from "@/ai_engine/inferenceClient";
import { StabilityFilter } from "@/stability/stabilityFilter";
import { CapturedFrame } from "@/types/frame";
import { CompositionMode, StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";

interface GuidanceControllerState {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  debugState: GuidanceDebugState;
  processing: boolean;
  error: string | null;
}

export function useGuidanceController(compositionMode: CompositionMode): GuidanceControllerState & {
  handleFrame: (frame: CapturedFrame) => void;
  reset: () => void;
} {
  const [stableGuidance, setStableGuidance] = useState<StableGuidance | null>(null);
  const [visionFeatures, setVisionFeatures] = useState<VisionFeatures | null>(null);
  const [debugState, setDebugState] = useState<GuidanceDebugState>({
    requestId: null,
    latestAcceptedFrameId: 0,
    latestProcessedFrameId: 0,
    latestRenderedFrameId: 0,
    droppedStaleResultCount: 0,
    visionLatencyMs: null,
    guidanceLatencyMs: null,
    totalLatencyMs: null,
    guidanceEngine: null
  });
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pipeline = useMemo(() => new GuidancePipeline({
    client: new ShutterMuseHttpClient({
      endpoint: appConfig.analyzeApiUrl ?? appConfig.shutterMuseApiUrl,
      timeoutMs: appConfig.guidanceTimeoutMs,
      mockEnabled: appConfig.mockEnabled
    }),
    stabilityFilter: new StabilityFilter(appConfig.stability),
    allowedFrameLag: appConfig.pipeline.allowedFrameLag,
    expiresMs: appConfig.stability.expiresMs
  }), []);

  useEffect(() => {
    pipeline.setCallbacks({
      onVisionFeatures: setVisionFeatures,
      onStableGuidance: setStableGuidance,
      onDebugState: setDebugState,
      onProcessingChange: setProcessing,
      onError: (pipelineError) => setError(pipelineError.message)
    });
    return () => pipeline.dispose();
  }, [pipeline]);

  useEffect(() => {
    pipeline.reset();
    setError(null);
  }, [compositionMode, pipeline]);

  const handleFrame = useCallback((frame: CapturedFrame) => {
    setError(null);
    pipeline.acceptFrame(frame, compositionMode);
  }, [compositionMode, pipeline]);

  const reset = useCallback(() => {
    pipeline.reset();
    setError(null);
  }, [pipeline]);

  return { stableGuidance, visionFeatures, debugState, processing, error, handleFrame, reset };
}
