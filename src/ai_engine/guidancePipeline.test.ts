import { describe, expect, it, vi } from "vitest";
import { GuidancePipeline } from "./guidancePipeline";
import { AnalyzeResult, GuidanceApiError, GuidanceEngineInput } from "./inferenceClient";
import { StabilityFilter } from "@/stability/stabilityFilter";

function result(frameId: number): AnalyzeResult {
  return { visionFeatures: null, guidance: { requestId: `req_${frameId}`, frameId, status: "success", priority: "hold", problem: { type: "none", description: "稳定" }, actions: [{ type: "hold", message: "保持角度" }], summary: "稳定", confidence: 0.9, timing: { visionMs: 1, guidanceMs: 1, totalMs: 2 } } };
}

function frame(frameId: number) {
  return { frameId, timestamp: frameId, image: { base64: "x", width: 10, height: 10, mimeType: "image/jpeg" } } as const;
}

describe("GuidancePipeline", () => {
  it("processes the active frame and only the latest pending frame", async () => {
    const resolvers: Array<(value: AnalyzeResult) => void> = [];
    const inputs: number[] = [];
    const client = { infer: vi.fn((input: GuidanceEngineInput) => { inputs.push(input.frame.frameId); return new Promise<AnalyzeResult>((resolve) => resolvers.push(resolve)); }) };
    const pipeline = new GuidancePipeline({ client, stabilityFilter: new StabilityFilter({ consistentFrames: 1, confidenceThreshold: 0, debounceMs: 0, expiresMs: 2500 }), allowedFrameLag: 1, expiresMs: 2500 });
    pipeline.acceptFrame(frame(1), "auto");
    pipeline.acceptFrame(frame(2), "auto");
    pipeline.acceptFrame(frame(3), "auto");
    expect(inputs).toEqual([1]);
    resolvers[0]?.(result(1));
    await vi.waitFor(() => expect(inputs).toEqual([1, 3]));
    resolvers[1]?.(result(3));
    pipeline.dispose();
  });

  it("reports model status without creating photography guidance", async () => {
    const error = new GuidanceApiError({
      code: "MODEL_BUSY",
      message: "AI 正在分析上一张画面",
      suggestion: "保持一下，很快就好",
      retryable: true,
      severity: "waiting"
    });
    const client = { infer: vi.fn(async () => { throw error; }) };
    const onError = vi.fn();
    const onStableGuidance = vi.fn();
    const onProcessingChange = vi.fn();
    const pipeline = new GuidancePipeline({
      client,
      stabilityFilter: new StabilityFilter({ consistentFrames: 1, confidenceThreshold: 0, debounceMs: 0, expiresMs: 2500 }),
      allowedFrameLag: 1,
      expiresMs: 2500
    });
    pipeline.setCallbacks({ onError, onStableGuidance, onProcessingChange });
    pipeline.acceptFrame(frame(1), "auto");
    await vi.waitFor(() => expect(onError).toHaveBeenCalledWith(error));
    expect(onStableGuidance).not.toHaveBeenCalled();
    expect(onProcessingChange).toHaveBeenLastCalledWith(false);
    pipeline.dispose();
  });

  it("does not update UI when a response arrives after disposal", async () => {
    let resolveRequest: ((value: AnalyzeResult) => void) | undefined;
    const client = {
      infer: vi.fn(() => new Promise<AnalyzeResult>((resolve) => { resolveRequest = resolve; }))
    };
    const onStableGuidance = vi.fn();
    const pipeline = new GuidancePipeline({
      client,
      stabilityFilter: new StabilityFilter({ consistentFrames: 1, confidenceThreshold: 0, debounceMs: 0, expiresMs: 2500 }),
      allowedFrameLag: 1,
      expiresMs: 2500
    });
    pipeline.setCallbacks({ onStableGuidance });
    pipeline.acceptFrame(frame(1), "auto");
    pipeline.dispose();
    onStableGuidance.mockClear();
    resolveRequest?.(result(1));
    await Promise.resolve();
    expect(onStableGuidance).not.toHaveBeenCalled();
  });
});
