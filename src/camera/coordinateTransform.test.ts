import { describe, expect, it } from "vitest";

import {
  applyAspectFillCrop,
  modelBBoxToPreviewBBox,
  previewPointToImagePoint
} from "./coordinateTransform";

describe("camera coordinate transforms", () => {
  it("maps equal-aspect normalized bounds directly", () => {
    expect(modelBBoxToPreviewBBox([0.1, 0.2, 0.9, 0.8], {
      image: { width: 1000, height: 1500 },
      preview: { width: 400, height: 600 },
      imageMirrored: false,
      previewMirrored: false
    })).toEqual([40, 120, 360, 480]);
  });

  it("accounts for aspect-fill horizontal crop", () => {
    expect(applyAspectFillCrop(
      { x: 0, y: 0 },
      { width: 1600, height: 1200 },
      { width: 300, height: 600 }
    )).toEqual({ x: -250, y: 0 });
  });

  it("clamps a horizontally cropped bbox to the preview", () => {
    expect(modelBBoxToPreviewBBox([0, 0.1, 1, 0.9], {
      image: { width: 1600, height: 900 },
      preview: { width: 300, height: 600 },
      imageMirrored: false,
      previewMirrored: false
    })).toEqual([0, 60, 300, 540]);
  });

  it("handles vertical crop in a landscape preview", () => {
    expect(modelBBoxToPreviewBBox([0.1, 0, 0.9, 1], {
      image: { width: 900, height: 1600 },
      preview: { width: 800, height: 400 },
      imageMirrored: false,
      previewMirrored: false
    })).toEqual([80, 0, 720, 400]);
  });

  it("mirrors front preview coordinates without changing image coordinates", () => {
    const context = {
      image: { width: 1000, height: 1000 },
      preview: { width: 500, height: 500 },
      imageMirrored: false,
      previewMirrored: true
    };
    expect(modelBBoxToPreviewBBox([0.1, 0.2, 0.3, 0.8], context)).toEqual([
      350, 100, 450, 400
    ]);
    expect(previewPointToImagePoint({ x: 400, y: 250 }, context)).toEqual({
      x: 200,
      y: 500
    });
  });

  it("produces horizontally symmetric boxes when preview mirroring changes", () => {
    const base = {
      image: { width: 1200, height: 1600 },
      preview: { width: 360, height: 640 },
      imageMirrored: false
    };
    const normal = modelBBoxToPreviewBBox([0.1, 0.2, 0.35, 0.8], { ...base, previewMirrored: false });
    const mirrored = modelBBoxToPreviewBBox([0.1, 0.2, 0.35, 0.8], { ...base, previewMirrored: true });
    expect(mirrored[0]).toBeCloseTo(base.preview.width - normal[2]);
    expect(mirrored[2]).toBeCloseTo(base.preview.width - normal[0]);
    expect(mirrored[1]).toBeCloseTo(normal[1]);
    expect(mirrored[3]).toBeCloseTo(normal[3]);
  });
});
