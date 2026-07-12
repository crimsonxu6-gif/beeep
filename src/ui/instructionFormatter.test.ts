import { describe, expect, it } from "vitest";

import { GuidanceOutput } from "@/types/guidance";
import { guidanceToInstructions } from "./instructionFormatter";

function guidance(messages: string[]): GuidanceOutput {
  return {
    requestId: "req_test",
    frameId: 1,
    status: "success",
    actions: messages.map((message, index) => index === 0
      ? { type: "move_camera", direction: "left", message }
      : { type: "adjust_distance", direction: "closer", message }),
    summary: "test",
    confidence: 0.9,
    timing: { visionMs: 0, guidanceMs: 1, totalMs: 1 }
  };
}

describe("guidanceToInstructions", () => {
  it("returns only the primary instruction for one action", () => {
    expect(guidanceToInstructions(guidance(["镜头稍微往左移"]))).toEqual({
      primary: "镜头稍微往左移",
      secondary: null
    });
  });

  it("returns primary and secondary instructions separately", () => {
    expect(guidanceToInstructions(guidance(["镜头稍微往左移", "再靠近人物一点"]))).toEqual({
      primary: "镜头稍微往左移",
      secondary: "再靠近人物一点"
    });
  });

  it("clamps each instruction to 16 unicode characters", () => {
    const value = "一二三四五六七八九十一二三四五六七";
    expect(Array.from(guidanceToInstructions(guidance([value])).primary)).toHaveLength(16);
  });
});
