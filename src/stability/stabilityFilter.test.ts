import { describe, expect, it } from "vitest";
import { GuidanceOutput } from "@/types/guidance";
import { StabilityFilter } from "./stabilityFilter";

function guidance(message: string): GuidanceOutput {
  return { requestId: "req", frameId: 1, status: "success", priority: "composition", problem: { type: "subject_position", description: "偏右" }, actions: [{ type: "move_camera", direction: "left", message }], summary: "偏右", confidence: 0.9, timing: { visionMs: 1, guidanceMs: 1, totalMs: 2 } };
}

describe("StabilityFilter", () => {
  it("treats synonymous messages as the same action", () => {
    const filter = new StabilityFilter({ consistentFrames: 2, confidenceThreshold: 0.5, debounceMs: 0, expiresMs: 2500 });
    expect(filter.next(guidance("往左一点"), 100)).toBeNull();
    expect(filter.next(guidance("向左移动"), 101)?.guidance.actions[0]?.message).toBe("向左移动");
  });

  it("expires and resets published guidance", () => {
    const filter = new StabilityFilter({ consistentFrames: 1, confidenceThreshold: 0.5, debounceMs: 0, expiresMs: 2000 });
    expect(filter.next(guidance("往左一点"), 100)).not.toBeNull();
    expect(filter.isExpired(2200)).toBe(true);
    filter.reset();
    expect(filter.isExpired(2200)).toBe(false);
  });
});
