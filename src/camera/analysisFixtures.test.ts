import { describe, expect, it, vi } from "vitest";

vi.mock("expo-asset", () => ({ Asset: { fromModule: vi.fn() } }));

import { ANALYSIS_FIXTURES, galleryFixtureSource } from "./analysisFixtures";

describe("analysis fixture inputs", () => {
  it("bundles the minimum reusable fixture set with metadata", () => {
    expect(ANALYSIS_FIXTURES).toHaveLength(8);
    expect(new Set(ANALYSIS_FIXTURES.map((item) => item.id)).size).toBe(8);
    expect(ANALYSIS_FIXTURES.every((item) => item.module !== undefined)).toBe(true);
  });

  it("registers a real landscape fixture and a phone-resolution fixture", () => {
    expect(ANALYSIS_FIXTURES.find((item) => item.id === "landscape_group")).toMatchObject({
      width: 1280,
      height: 960,
      orientation: "landscape_right",
      bytes: 284595
    });
    expect(ANALYSIS_FIXTURES.find((item) => item.id === "large_portrait")).toMatchObject({
      width: 3024,
      height: 4032,
      bytes: 1174344
    });
  });

  it("normalizes gallery assets into the unified source type", () => {
    const source = galleryFixtureSource(
      { uri: "file:///gallery.jpg", width: 1600, height: 900 },
      {
        cameraFacing: "front",
        imageMirrored: false,
        previewMirrored: true,
        deviceOrientation: "landscape_right"
      }
    );
    expect(source).toMatchObject({
      uri: "file:///gallery.jpg",
      width: 1600,
      height: 900,
      source: "gallery",
      cameraFacing: "front",
      previewMirrored: true,
      deviceOrientation: "landscape_right"
    });
  });
});
