import { beforeEach, describe, expect, it, vi } from "vitest";

const native = vi.hoisted(() => ({
  manipulateAsync: vi.fn(async () => ({
    uri: "file:///processed.jpg",
    width: 768,
    height: 1024
  }))
}));

vi.mock("expo-image-manipulator", () => ({
  manipulateAsync: native.manipulateAsync,
  SaveFormat: { JPEG: "jpeg" }
}));

vi.mock("expo-file-system", () => ({
  File: class File {
    size: number;
    constructor(public uri: string) {
      this.size = uri.includes("processed") ? 82_000 : 260_000;
    }
  }
}));

import { AnalysisFrameController } from "./AnalysisFrameController";

describe("unified analysis source processing", () => {
  beforeEach(() => native.manipulateAsync.mockClear());

  it("runs a fixture through the same resize and JPEG processing boundary", async () => {
    const controller = new AnalysisFrameController();
    const frame = await controller.processAnalysisSourceFrame({
      uri: "file:///fixture-source.jpg",
      width: 960,
      height: 1280,
      cameraFacing: "front",
      imageMirrored: false,
      previewMirrored: true,
      deviceOrientation: "portrait",
      source: "fixture"
    }, 100_000, { tapTimestamp: 10, previewWidth: 1080, previewHeight: 1920 });

    expect(native.manipulateAsync).toHaveBeenCalledWith(
      "file:///fixture-source.jpg",
      [{ resize: { width: 768 } }],
      expect.objectContaining({ base64: false, compress: 0.7, format: "jpeg" })
    );
    expect(frame.image).toMatchObject({
      uri: "file:///processed.jpg",
      width: 768,
      height: 1024,
      mimeType: "image/jpeg",
      originalBytes: 260_000,
      processedBytes: 82_000,
      originalWidth: 960,
      originalHeight: 1280
    });
    expect(frame.capture).toMatchObject({
      source: "fixture",
      cameraFacing: "front",
      previewMirrored: true,
      tapTimestamp: 10
    });
  });

  it("converts camera capture into the same source processor", async () => {
    const controller = new AnalysisFrameController();
    const camera = {
      takePictureAsync: vi.fn(async () => ({ uri: "file:///camera.jpg", width: 1280, height: 960 }))
    };
    const frame = await controller.captureAnalysisFrame(camera as never, 1, { cameraFacing: "back" });
    expect(frame?.capture?.source).toBe("camera");
    expect(native.manipulateAsync).toHaveBeenCalledWith(
      "file:///camera.jpg",
      [{ resize: { height: 768 } }],
      expect.any(Object)
    );
  });
});
