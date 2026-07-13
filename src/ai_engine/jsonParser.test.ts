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

  it("keeps two instructions and a composition box", () => {
    const parsed = validateGuidanceOutput({
      frame_id: 1,
      request_id: "req_test",
      actions: [
        { type: "move_camera", direction: "left", message: "镜头稍微往左移" },
        { type: "adjust_distance", direction: "closer", message: "再靠近人物一点" }
      ],
      confidence: 0.8,
      summary: "test",
      composition: { decision: "refine", bbox_norm: [0.1, 0.1, 0.8, 0.9] },
      subject_preflight: {
        state: "uncertain",
        detected: true,
        allow_shuttermuse: true,
        confidence: 0.5,
        face_detected: true,
        pose_detected: false,
        detection_source: "face",
        face_confidence: 0.5,
        pose_confidence: 0,
        visible_pose_keypoints: 0,
        consecutive_missing: 0,
        consecutive_uncertain: 1,
        history_used: false,
        blocking_enabled: false,
        blocked_model_call: false,
        reason_code: "face_low_confidence"
      },
      timing: { preflight_ms: 12 }
    });
    expect(parsed.actions).toHaveLength(2);
    expect(parsed.composition?.bboxNorm).toEqual([0.1, 0.1, 0.8, 0.9]);
    expect(parsed.timing.preflightMs).toBe(12);
    expect(parsed.subjectPreflight?.state).toBe("uncertain");
    expect(parsed.subjectPreflight?.allowShutterMuse).toBe(true);
    expect(parsed.subjectPreflight?.detectionSource).toBe("face");
    expect(parsed.subjectPreflight?.consecutiveUncertain).toBe(1);
  });
});
