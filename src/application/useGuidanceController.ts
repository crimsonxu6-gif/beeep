import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { appConfig } from "@/config";
import { GuidanceDebugState, GuidancePipeline } from "@/ai_engine/guidancePipeline";
import { GuidanceApiError, ShutterMuseHttpClient } from "@/ai_engine/inferenceClient";
import { StabilityFilter } from "@/stability/stabilityFilter";
import { CapturedFrame } from "@/types/frame";
import { CompositionMode, ModelStatus, StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { analysisWaitingStatus } from "./analysisState";

interface GuidanceControllerState {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  debugState: GuidanceDebugState;
  processing: boolean;
  modelStatus: ModelStatus | null;
}

export function useGuidanceController(compositionMode: CompositionMode): GuidanceControllerState & {
  handleFrame: (frame: CapturedFrame) => void;
  beginAnalysis: () => void;
  cancelAnalysis: () => void;
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
    guidanceEngine: null,
    errorCode: null,
    captureMs: null,
    preprocessMs: null,
    payloadBytes: null,
    requestBodyBytes: null,
    networkAndServerMs: null,
    clientNetworkOverheadMs: null,
    renderMs: null,
    tapToOverlayMs: null,
    httpStatus: null,
    uploadMode: null,
    apiMode: null,
    captureSource: null,
    sourceDimensions: null,
    processedDimensions: null,
    sourceBytes: null,
    processedBytes: null
  });
  const [processing, setProcessing] = useState(false);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const waitingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearWaitingTimer = useCallback(() => {
    if (waitingTimerRef.current) clearTimeout(waitingTimerRef.current);
    waitingTimerRef.current = null;
  }, []);

  const pipeline = useMemo(() => new GuidancePipeline({
    client: new ShutterMuseHttpClient({
      endpoint: appConfig.analyzeApiUrl ?? appConfig.shutterMuseApiUrl,
      timeoutMs: appConfig.guidanceTimeoutMs,
      mockEnabled: appConfig.mockEnabled
    }),
    stabilityFilter: new StabilityFilter({
      ...appConfig.stability,
      consistentFrames: appConfig.guidanceTriggerMode === "manual"
        ? 1
        : appConfig.stability.consistentFrames
    }),
    allowedFrameLag: appConfig.pipeline.allowedFrameLag,
    expiresMs: appConfig.stability.expiresMs
  }), []);

  useEffect(() => {
    pipeline.setCallbacks({
      onVisionFeatures: setVisionFeatures,
      onStableGuidance: setStableGuidance,
      onDebugState: setDebugState,
      onProcessingChange: setProcessing,
      onSuccess: () => {
        clearWaitingTimer();
        setModelStatus(null);
      },
      onError: (pipelineError) => {
        clearWaitingTimer();
        if (pipelineError instanceof GuidanceApiError) {
          setModelStatus(pipelineError.status);
          return;
        }
        setModelStatus({
          code: "UNKNOWN_ERROR",
          message: "AI 暂时无法使用",
          suggestion: "可以稍后再来试试",
          retryable: true,
          severity: "error"
        });
      }
    });
    return () => {
      clearWaitingTimer();
      pipeline.dispose();
    };
  }, [clearWaitingTimer, pipeline]);

  useEffect(() => {
    pipeline.reset();
    clearWaitingTimer();
    setModelStatus(null);
  }, [clearWaitingTimer, compositionMode, pipeline]);

  const handleFrame = useCallback((frame: CapturedFrame) => {
    pipeline.acceptFrame(frame, compositionMode);
  }, [compositionMode, pipeline]);

  const beginAnalysis = useCallback(() => {
    clearWaitingTimer();
    const initial = analysisWaitingStatus(0);
    setModelStatus({
      code: "ANALYZING_COMPOSITION",
      ...initial,
      retryable: false,
      severity: "waiting"
    });
    waitingTimerRef.current = setTimeout(() => {
      const delayed = analysisWaitingStatus(2000);
      setModelStatus({
        code: "ANALYZING_COMPOSITION",
        ...delayed,
        retryable: false,
        severity: "waiting"
      });
    }, 2000);
  }, [clearWaitingTimer]);

  const cancelAnalysis = useCallback(() => {
    clearWaitingTimer();
    setModelStatus(null);
  }, [clearWaitingTimer]);

  const reset = useCallback(() => {
    pipeline.reset();
    clearWaitingTimer();
    setModelStatus(null);
  }, [clearWaitingTimer, pipeline]);

  return {
    stableGuidance,
    visionFeatures,
    debugState,
    processing,
    modelStatus,
    handleFrame,
    beginAnalysis,
    cancelAnalysis,
    reset
  };
}
