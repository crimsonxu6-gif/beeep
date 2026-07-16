import { describe, expect, it } from "vitest";

import {
  DEFAULT_FIXTURE_SETTINGS,
  previewAspectRatio,
  simulatedPreviewSize
} from "./fixtureSession";

describe("fixture preview simulation", () => {
  it("uses portrait and landscape ratios without stretching", () => {
    expect(previewAspectRatio("9:16", "portrait")).toBeCloseTo(9 / 16);
    expect(previewAspectRatio("16:9", "landscape_right")).toBeCloseTo(16 / 9);
    expect(previewAspectRatio("1:1", "landscape_right")).toBe(1);
  });

  it("fits a selected ratio inside the simulated device", () => {
    const portrait = simulatedPreviewSize(DEFAULT_FIXTURE_SETTINGS);
    expect(portrait.width).toBe(1080);
    expect(portrait.height).toBe(1920);
    const landscape = simulatedPreviewSize({
      ...DEFAULT_FIXTURE_SETTINGS,
      deviceOrientation: "landscape_right",
      previewRatio: "16:9"
    });
    expect(landscape.width / landscape.height).toBeCloseTo(16 / 9, 2);
    expect(landscape.width).toBeLessThanOrEqual(1920);
  });
});
