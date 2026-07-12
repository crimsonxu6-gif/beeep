import { afterEach, describe, expect, it, vi } from "vitest";

import { GuidanceEngineInput, ShutterMuseHttpClient } from "./inferenceClient";

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
});
