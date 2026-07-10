import { GuidanceOutput } from "@/types/guidance";

export function createMockGuidance(frameId: number): GuidanceOutput {
  return {
    requestId: `mock_${frameId}`,
    frameId,
    status: "success",
    guidanceEngine: "mock",
    priority: "hold",
    problem: { type: "none", description: "开发模拟" },
    actions: [{ type: "hold", message: "保持角度", confidence: 0.82 }],
    message: "保持角度",
    reason: "开发环境显式启用了模拟指导",
    summary: "开发模拟",
    confidence: 0.82,
    timing: { visionMs: 0, guidanceMs: 0, totalMs: 0 }
  };
}
