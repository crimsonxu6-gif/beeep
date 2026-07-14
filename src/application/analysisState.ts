import { AppRoute } from "./navigation";
import { GuidanceTriggerMode } from "@/config";

export function isAutomaticAnalysisEnabled(
  route: AppRoute,
  permissionGranted: boolean,
  processing: boolean,
  capturing: boolean,
  triggerMode: GuidanceTriggerMode = "continuous"
): boolean {
  return triggerMode !== "manual" && route === "camera" && permissionGranted && !processing && !capturing;
}

export function canRequestManualAnalysis(
  triggerMode: GuidanceTriggerMode,
  processing: boolean,
  capturePending: boolean,
  capturingPhoto: boolean
): boolean {
  return triggerMode === "manual" && !processing && !capturePending && !capturingPhoto;
}

export function analysisWaitingStatus(elapsedMs: number) {
  return elapsedMs >= 2000
    ? { message: "正在寻找更好的取景", suggestion: "再保持一下" }
    : { message: "正在分析构图", suggestion: "保持画面稳定" };
}
