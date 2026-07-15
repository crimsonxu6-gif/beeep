import { describe, expect, it } from "vitest";

import { ANALYSIS_CAPTURE_OPTIONS, buildAnalysisImagePlan } from "./analysisImagePlan";

describe("analysis image plan", () => {
  it("captures an orientation-correct file without base64", () => {
    expect(ANALYSIS_CAPTURE_OPTIONS).toEqual({
      base64: false,
      quality: 0.8,
      skipProcessing: false,
      shutterSound: false
    });
  });

  it("resizes portrait and landscape images by one dimension only", () => {
    expect(buildAnalysisImagePlan(1080, 1920, 768, 0.7)).toEqual({
      resize: { width: 768 },
      jpegQuality: 0.7
    });
    expect(buildAnalysisImagePlan(1920, 1080, 768, 0.7)).toEqual({
      resize: { height: 768 },
      jpegQuality: 0.7
    });
  });

  it("does not upscale a small analysis image", () => {
    expect(buildAnalysisImagePlan(640, 900, 768, 0.7).resize).toEqual({ width: 640 });
  });
});
