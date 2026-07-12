import { VisionFeatures } from "@/types/vision";

const actionConfidence = { type: "number", minimum: 0, maximum: 1 };
const message = { type: "string", maxLength: 16 };

export const guidanceJsonSchema = {
  type: "object",
  required: ["priority", "problem", "actions", "message", "reason", "summary", "confidence"],
  additionalProperties: false,
  properties: {
    priority: {
      enum: ["subject", "lighting", "composition", "pose", "camera", "distance", "angle", "hold"]
    },
    problem: {
      type: "object",
      required: ["type", "description"],
      additionalProperties: false,
      properties: {
        type: { type: "string", maxLength: 40 },
        description: { type: "string", maxLength: 48 }
      }
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
              direction: { enum: ["left", "right", "up", "down"] },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "direction", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "adjust_distance" },
              direction: { enum: ["closer", "farther"] },
              message,
              confidence: actionConfidence
            }
          },
          {
            type: "object",
            required: ["type", "direction", "message"],
            additionalProperties: false,
            properties: {
              type: { const: "adjust_angle" },
              direction: { enum: ["lower", "raise", "tilt_left", "tilt_right", "straighten"] },
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
    message,
    reason: { type: "string", maxLength: 80 },
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
    "# Decision Rule",
    "先判断当前画面，再找最大问题，只给用户下一秒能执行的动作。",
    "用户只看到 message；problem 和 reason 只给开发调试使用。",
    "每次最多输出 1-2 个 actions，优先 1 个。",
    "如果没有明显问题，不要强行指导，输出 hold。",
    "",
    "# Decision Priority",
    "1. 人物是否清晰可见",
    "2. 光线是否影响照片质量",
    "3. 构图是否明显错误",
    "4. 人物姿态是否自然",
    "5. 距离或角度是否明显需要调整",
    "",
    "# Action Types",
    "move_camera: 只表示手机平移，direction 为 left/right/up/down。",
    "adjust_distance: 距离调整，direction 为 closer/farther。",
    "adjust_angle: 角度调整，direction 为 lower/raise/tilt_left/tilt_right/straighten。",
    "adjust_pose: 人物姿势。",
    "framing_hint: 构图建议。",
    "lighting_hint: 光线建议。",
    "hold: 保持当前角度。",
    "",
    "# Output Rules",
    "必须严格 JSON。禁止 Markdown。禁止解释文字。",
    "priority 必须是 subject、lighting、composition、pose、camera、distance、angle、hold 之一。",
    "message 必须是中文，不超过 16 个字，普通人能马上理解。",
    "reason 用于开发调试，不给用户展示，简短说明为什么这样判断。",
    "不要输出黄金比例、黄金时刻、视觉重心、色彩心理学等术语。",
    "",
    "# Vision Context",
    JSON.stringify(visionFeatures)
  ].join("\n");
}
