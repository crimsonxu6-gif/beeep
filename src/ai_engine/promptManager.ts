import { VisionFeatures } from "@/types/vision";

const actionConfidence = { type: "number", minimum: 0, maximum: 1 };
const message = { type: "string", maxLength: 10 };

export const guidanceJsonSchema = {
  type: "object",
  required: ["priority", "actions", "summary", "confidence"],
  additionalProperties: false,
  properties: {
    priority: {
      enum: ["subject", "lighting", "composition", "pose", "camera", "hold"]
    },
    actions: {
      type: "array",
      maxItems: 2,
      items: {
        anyOf: [
          {
            type: "object",
            required: ["type", "direction", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "move_camera" },
              direction: { enum: ["left", "right", "up", "down", "forward", "back"] },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "adjust_pose" },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "framing_hint" },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "lighting_hint" },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "hold" },
              message,
              confidence: actionConfidence
            }
          }
        ]
      }
    },
    summary: { type: "string", maxLength: 32 },
    confidence: { type: "number", minimum: 0, maximum: 1 }
  }
} as const;

export function buildGuidancePrompt(visionFeatures: VisionFeatures): string {
  return [
    "# System Prompt",
    "你是一名世界级手机摄影指导 AI。",
    "你不是摄影评论家，而是站在用户身边的实时摄影助手。",
    "你的任务是在用户按快门前，判断当前画面，找最大问题，给一个最有效动作。",
    "",
    "# User Experience Rules",
    "禁止长篇解释、摄影理论、专业术语、复杂参数建议。",
    "优先输出动作，例如：往左一点、靠近一点、手机低一点、转向光源、保持不动。",
    "每次最多输出 1-2 个 actions。",
    "如果没有明显问题，不要强行指导，输出 hold。",
    "",
    "# Decision Priority",
    "1. 人物是否清晰可见",
    "2. 光线是否影响照片质量",
    "3. 构图是否明显错误",
    "4. 人物姿态是否自然",
    "5. 其他优化",
    "",
    "# Output Rules",
    "必须严格 JSON。禁止 Markdown。禁止解释文字。",
    "priority 必须是 subject、lighting、composition、pose、camera、hold 之一。",
    "action.type 只允许 move_camera、adjust_pose、framing_hint、lighting_hint、hold。",
    "message 必须是中文，不超过 10 个字，普通人能马上理解。",
    "move_camera.direction 只允许 left/right/up/down/forward/back。",
    "不要输出黄金比例、黄金时刻、视觉重心、色彩心理学等术语。",
    "",
    "# Vision Context",
    JSON.stringify(visionFeatures)
  ].join("\n");
}
