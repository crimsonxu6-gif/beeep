import { expect, it } from "vitest";
import { isAutomaticAnalysisEnabled } from "./analysisState";

it("pauses automatic analysis during capture and outside camera", () => {
  expect(isAutomaticAnalysisEnabled("camera", true, false, false)).toBe(true);
  expect(isAutomaticAnalysisEnabled("camera", true, false, true)).toBe(false);
  expect(isAutomaticAnalysisEnabled("photoPreview", true, false, false)).toBe(false);
});
