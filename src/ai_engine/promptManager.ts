import { VisionFeatures } from "@/types/vision";

export const guidanceJsonSchema = {
  type: "object",
  required: ["actions", "summary", "confidence"],
  additionalProperties: false,
  properties: {
    actions: {
      type: "array",
      maxItems: 3,
      items: {
        anyOf: [
          {
            type: "object",
            required: ["type", "direction", "strength"],
            additionalProperties: false,
            properties: {
              type: { const: "move_camera" },
              direction: { enum: ["left", "right", "up", "down", "forward", "back", "hold"] },
              strength: { enum: ["low", "medium", "high"] }
            }
          },
          {
            type: "object",
            required: ["type", "instruction"],
            additionalProperties: false,
            properties: {
              type: { const: "adjust_pose" },
              instruction: { type: "string", maxLength: 48 },
              strength: { enum: ["low", "medium", "high"] }
            }
          },
          {
            type: "object",
            required: ["type", "instruction"],
            additionalProperties: false,
            properties: {
              type: { const: "framing_hint" },
              instruction: { type: "string", maxLength: 48 },
              direction: { enum: ["left", "right", "up", "down", "forward", "back", "hold"] },
              strength: { enum: ["low", "medium", "high"] }
            }
          }
        ]
      }
    },
    summary: { type: "string", maxLength: 80 },
    confidence: { type: "number", minimum: 0, maximum: 1 }
  }
} as const;

export function buildGuidancePrompt(visionFeatures: VisionFeatures): string {
  return [
    "You are the AI Guidance Engine for a mobile photography assistant.",
    "Return strict JSON only. No markdown. No explanation.",
    "Give executable capture-time actions only.",
    "Allowed action types: move_camera, adjust_pose, framing_hint.",
    "Keep actions stable and concise.",
    `Vision features: ${JSON.stringify(visionFeatures)}`
  ].join("\n");
}
