import { describe, expect, it } from "vitest";
import { validateGuidanceOutput } from "./jsonParser";

function output(action: Record<string, unknown>) {
  return { frame_id: 1, request_id: "req_test", actions: [action], confidence: 0.8, summary: "test", timing: {} };
}

describe("guidance parser", () => {
  it.each([
    { type: "move_camera", direction: "center", message: "保持" },
    { type: "adjust_distance", direction: "inside", message: "靠近" },
    { type: "adjust_angle", direction: "center", message: "摆正" }
  ])("rejects illegal directional action %#", (action) => {
    expect(() => validateGuidanceOutput(output(action))).toThrow(/Invalid/);
  });

  it("requires frame_id", () => {
    expect(() => validateGuidanceOutput({ actions: [], confidence: 0.8 })).toThrow(/frame_id/);
  });
});
