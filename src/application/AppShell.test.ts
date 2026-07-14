import { expect, it } from "vitest";
import {
  analysisWaitingStatus,
  canRequestManualAnalysis,
  isAutomaticAnalysisEnabled
} from "./analysisState";

it("pauses automatic analysis during capture and outside camera", () => {
  expect(isAutomaticAnalysisEnabled("camera", true, false, false)).toBe(true);
  expect(isAutomaticAnalysisEnabled("camera", true, false, true)).toBe(false);
  expect(isAutomaticAnalysisEnabled("photoPreview", true, false, false)).toBe(false);
});

it("manual mode only submits after an enabled user action", () => {
  expect(isAutomaticAnalysisEnabled("camera", true, false, false, "manual")).toBe(false);
  expect(canRequestManualAnalysis("manual", false, false, false)).toBe(true);
  expect(canRequestManualAnalysis("manual", true, false, false)).toBe(false);
  expect(canRequestManualAnalysis("manual", false, true, false)).toBe(false);
  expect(canRequestManualAnalysis("manual", false, false, true)).toBe(false);
});

it("continuous and stable auto remain available for development", () => {
  expect(isAutomaticAnalysisEnabled("camera", true, false, false, "continuous")).toBe(true);
  expect(isAutomaticAnalysisEnabled("camera", true, false, false, "stable_auto")).toBe(true);
});

it("uses staged analysis copy for a multi-second wait", () => {
  expect(analysisWaitingStatus(0)).toEqual({
    message: "正在分析构图",
    suggestion: "保持画面稳定"
  });
  expect(analysisWaitingStatus(2000)).toEqual({
    message: "正在寻找更好的取景",
    suggestion: "再保持一下"
  });
});
