import {
  ActionStrength,
  GuidanceAction,
  GuidanceOutput,
  GuidancePriority,
  MoveDirection
} from "@/types/guidance";

const actionTypes = new Set(["move_camera", "adjust_pose", "framing_hint", "lighting_hint", "hold"]);
const directions = new Set(["left", "right", "up", "down", "forward", "back", "hold"]);
const strengths = new Set(["low", "medium", "high"]);
const priorities = new Set(["subject", "lighting", "composition", "pose", "camera", "hold"]);

export class GuidanceParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GuidanceParseError";
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new GuidanceParseError("Expected a JSON object.");
  }

  return value as Record<string, unknown>;
}

function extractJsonObject(raw: string): string {
  const trimmed = raw.trim();
  const fenceMatch = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  const candidate = fenceMatch?.[1]?.trim() ?? trimmed;

  if (candidate.startsWith("{") && candidate.endsWith("}")) {
    return candidate;
  }

  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    throw new GuidanceParseError("No JSON object found in model output.");
  }

  return candidate.slice(start, end + 1);
}

function clamp01(value: unknown, fallback: number): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.min(1, Math.max(0, numberValue)) : fallback;
}

function normalizeStrength(value: unknown): ActionStrength {
  return strengths.has(String(value)) ? (String(value) as ActionStrength) : "medium";
}

function normalizeDirection(value: unknown): MoveDirection {
  return directions.has(String(value)) ? (String(value) as MoveDirection) : "hold";
}

function normalizePriority(value: unknown): GuidancePriority | undefined {
  return priorities.has(String(value)) ? (String(value) as GuidancePriority) : undefined;
}

function normalizeMessage(value: unknown): string {
  return typeof value === "string" ? Array.from(value.trim()).slice(0, 10).join("") : "";
}

function normalizeInstruction(value: unknown): string {
  return typeof value === "string" ? value.trim().slice(0, 48) : "";
}

function messageFromInstruction(value: unknown): string {
  const text = normalizeInstruction(value).toLowerCase();
  if (!text) {
    return "";
  }

  if (text.includes("backlight") || text.includes("light source")) {
    return "转向光源";
  }
  if (text.includes("exposure") || text.includes("dark")) {
    return "提高曝光";
  }
  if (text.includes("background") || text.includes("clutter")) {
    return "背景简洁";
  }
  if (text.includes("shoulder")) {
    return "肩膀放松";
  }
  if (text.includes("head") && text.includes("left")) {
    return "头左一点";
  }
  if (text.includes("head") && text.includes("right")) {
    return "头右一点";
  }
  if (text.includes("hold") || text.includes("steady")) {
    return "保持角度";
  }
  if (text.includes("subject")) {
    return "寻找主体";
  }

  return "";
}

function fallbackMoveMessage(direction: MoveDirection): string {
  const text = {
    left: "往左一点",
    right: "往右一点",
    up: "抬高一点",
    down: "压低一点",
    forward: "靠近一点",
    back: "后退一点",
    hold: "保持角度"
  } as const;

  return text[direction];
}

function actionMessage(action: Record<string, unknown>, fallback: string): string {
  return normalizeMessage(action.message) || messageFromInstruction(action.instruction) || fallback;
}

function withOptionalMetadata<T extends GuidanceAction>(
  action: T,
  raw: Record<string, unknown>
): T {
  if (raw.confidence !== undefined) {
    action.confidence = clamp01(raw.confidence, 0.7);
  }

  if (raw.strength !== undefined) {
    action.strength = normalizeStrength(raw.strength);
  }

  return action;
}

function validateAction(value: unknown): GuidanceAction | null {
  const action = asRecord(value);
  const type = String(action.type);
  if (!actionTypes.has(type)) {
    return null;
  }

  if (type === "move_camera") {
    const direction = normalizeDirection(action.direction);
    return withOptionalMetadata(
      {
        type,
        direction,
        message: actionMessage(action, fallbackMoveMessage(direction))
      },
      action
    );
  }

  if (type === "hold") {
    return withOptionalMetadata(
      {
        type,
        message: actionMessage(action, "保持角度")
      },
      action
    );
  }

  if (type === "lighting_hint") {
    const message = actionMessage(action, "调整光线");
    if (!message) {
      return null;
    }

    return withOptionalMetadata(
      {
        type,
        message,
        instruction: normalizeInstruction(action.instruction) || message
      },
      action
    );
  }

  if (type === "adjust_pose") {
    const message = actionMessage(action, "姿势微调");
    if (!message) {
      return null;
    }

    return withOptionalMetadata(
      {
        type,
        message,
        instruction: normalizeInstruction(action.instruction) || message
      },
      action
    );
  }

  const message = actionMessage(action, "调整构图");
  if (!message) {
    return null;
  }

  const framingAction: GuidanceAction = {
    type: "framing_hint",
    message,
    instruction: normalizeInstruction(action.instruction) || message
  };

  if (action.direction) {
    framingAction.direction = normalizeDirection(action.direction);
  }

  return withOptionalMetadata(framingAction, action);
}

export function validateGuidanceOutput(value: unknown): GuidanceOutput {
  const root = asRecord(value);
  if (!Array.isArray(root.actions)) {
    throw new GuidanceParseError("Missing actions array.");
  }

  const actions = root.actions.map(validateAction).filter((action): action is GuidanceAction => Boolean(action));
  const confidence = Number(root.confidence);

  if (!Number.isFinite(confidence)) {
    throw new GuidanceParseError("Missing confidence number.");
  }

  const output: GuidanceOutput = {
    actions: actions.slice(0, 2),
    summary: typeof root.summary === "string" ? root.summary.slice(0, 80) : "",
    confidence: Math.min(1, Math.max(0, confidence))
  };

  const priority = normalizePriority(root.priority);
  if (priority) {
    output.priority = priority;
  }

  if (typeof root.frame_id === "number") {
    output.frameId = root.frame_id;
  } else if (typeof root.frameId === "number") {
    output.frameId = root.frameId;
  }

  return output;
}

export function parseGuidanceJson(raw: string): GuidanceOutput {
  try {
    return validateGuidanceOutput(JSON.parse(extractJsonObject(raw)));
  } catch (error) {
    if (error instanceof GuidanceParseError) {
      throw error;
    }

    throw new GuidanceParseError(error instanceof Error ? error.message : String(error));
  }
}
