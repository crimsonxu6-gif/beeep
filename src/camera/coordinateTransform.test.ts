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
});
