import { afterEach, describe, expect, it, vi } from "vitest";

import {
  GuidanceEngineInput,
  multipartImagePart,
  multipartMetadata,
  ShutterMuseHttpClient
} from "./inferenceClient";

const input: GuidanceEngineInput = {
  compositionMode: "auto",
  frame: {
    frameId: 1,
    timestamp: 1,
    image: { base64: "x", width: 10, height: 10, mimeType: "image/jpeg" }
  }
};

afterEach(() => vi.unstubAllGlobals());

describe("ShutterMuseHttpClient model status", () => {
  it("returns deterministic mock success without a backend endpoint", async () => {
    const client = new ShutterMuseHttpClient({
      endpoint: undefined,
      timeoutMs: 100,
      mockEnabled: false,
      apiMode: "mock_success",
      uploadMode: "multipart"
    });
    const result = await client.infer(input);
    expect(result.guidance.composition?.bboxNorm).toEqual([0.15, 0.1, 0.8, 0.9]);
    expect(result.guidance.actions[0]?.message).toBe("镜头稍微往左移");
    expect(result.guidance.clientTiming?.apiMode).toBe("mock_success");
  });

  it("returns structured mock errors and recovers control to the caller", async () => {
    const client = new ShutterMuseHttpClient({ endpoint: undefined, timeoutMs: 100, mockEnabled: false, apiMode: "mock_error" });
    await expect(client.infer(input)).rejects.toMatchObject({
      status: { code: "INVALID_MODEL_OUTPUT", retryable: true }
    });
  });

  it.each([
    ["http_500", "HTTP_500"],
    ["http_502", "HTTP_502"],
    ["http_503", "HTTP_503"],
    ["http_504", "HTTP_504"],
    ["invalid_json", "INVALID_MODEL_OUTPUT"],
    ["missing_bbox", "INVALID_MODEL_OUTPUT"],
    ["bbox_safety_rejected", "BBOX_SAFETY_REJECTED"]
  ] as const)("maps mock failure %s to %s", async (failureScenario, code) => {
    const client = new ShutterMuseHttpClient({
      endpoint: undefined,
      timeoutMs: 100,
      mockEnabled: false,
      apiMode: "mock_error",
      failureScenario
    });
    await expect(client.infer(input)).rejects.toMatchObject({ status: { code } });
  });

  it("aborts mock timeouts using the normal timeout path", async () => {
    const client = new ShutterMuseHttpClient({ endpoint: undefined, timeoutMs: 5, mockEnabled: false, apiMode: "mock_timeout" });
    await expect(client.infer(input)).rejects.toMatchObject({ status: { code: "MODEL_TIMEOUT" } });
  });

  it("maps MODEL_BUSY to a non-severe waiting status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      status: "error",
      error: {
        code: "MODEL_BUSY",
        message: "AI 正在分析上一张画面",
        suggestion: "保持一下，很快就好",
        retryable: true,
        severity: "waiting"
      }
    }), { status: 429 })));
    const client = new ShutterMuseHttpClient({ endpoint: "http://test/v1/analyze", timeoutMs: 1000, mockEnabled: false });
    await expect(client.infer(input)).rejects.toMatchObject({
      status: { code: "MODEL_BUSY", severity: "waiting", suggestion: "保持一下，很快就好" }
    });
  });

  it("maps fetch failures to a network suggestion", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("offline"); }));
    const client = new ShutterMuseHttpClient({ endpoint: "http://test/v1/analyze", timeoutMs: 1000, mockEnabled: false });
    await expect(client.infer(input)).rejects.toMatchObject({
      status: {
        code: "NETWORK_ERROR",
        message: "网络连接不太稳定",
        suggestion: "检查网络后再试"
      }
    });
  });

  it("maps simulated offline mode to the normal network recovery status", async () => {
    const client = new ShutterMuseHttpClient({
      endpoint: "http://test/v1/analyze",
      timeoutMs: 100,
      mockEnabled: false,
      networkProfile: "offline"
    });
    await expect(client.infer(input)).rejects.toMatchObject({ status: { code: "NETWORK_ERROR" } });
  });

  it("maps invalid JSON to invalid model output instead of a network error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("not-json", { status: 200 })));
    const client = new ShutterMuseHttpClient({ endpoint: "http://test/v1/analyze", timeoutMs: 1000, mockEnabled: false });
    await expect(client.infer(input)).rejects.toMatchObject({ status: { code: "INVALID_MODEL_OUTPUT" } });
  });
});

describe("analysis multipart request", () => {
  const multipartInput: GuidanceEngineInput = {
    compositionMode: "thirds_left",
    frame: {
      frameId: 7,
      timestamp: 123,
      image: {
        uri: "file:///analysis.jpg",
        width: 768,
        height: 1024,
        mimeType: "image/jpeg",
        originalBytes: 250000,
        processedBytes: 88000
      },
      capture: {
        source: "fixture",
        tapTimestamp: 100,
        captureStartedAt: 101,
        captureCompletedAt: 103,
        preprocessCompletedAt: 120,
        cameraFacing: "front",
        imageMirrored: false,
        previewMirrored: true,
        deviceOrientation: "portrait",
        previewWidth: 1080,
        previewHeight: 1920
      }
    }
  };

  it("includes the image part and every analysis metadata field", () => {
    expect(multipartImagePart(multipartInput)).toEqual({
      uri: "file:///analysis.jpg",
      name: "analysis-7.jpg",
      type: "image/jpeg"
    });
    expect(multipartMetadata(multipartInput, "fixture_stream", 125)).toMatchObject({
      frame_id: 7,
      timestamp: 123,
      stream_id: "fixture_stream",
      target_ratio: "3:4",
      composition_mode: "thirds_left",
      language: "zh-CN",
      requires_person: true,
      camera_facing: "front",
      image_mirrored: false,
      device_orientation: "portrait",
      preview_width: 1080,
      preview_height: 1920,
      image_width: 768,
      image_height: 1024,
      upload_mode: "multipart"
    });
  });
});
