import {
  ActionStrength,
  GuidanceAction,
  GuidanceOutput,
  MoveDirection
} from "@/types/guidance";

const actionTypes = new Set(["move_camera", "adjust_pose", "framing_hint"]);
const directions = new Set(["left", "right", "up", "down", "forward", "back", "hold"]);
const strengths = new Set(["low", "medium", "high"]);

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

function normalizeStrength(value: unknown): ActionStrength {
  return strengths.has(String(value)) ? (String(value) as ActionStrength) : "medium";
}

function normalizeDirection(value: unknown): MoveDirection {
  return directions.has(String(value)) ? (String(value) as MoveDirection) : "hold";
}

function normalizeInstruction(value: unknown): string {
  if (typeof value !== "string") {
    return "";
  }

  return value.trim().slice(0, 48);
}

function validateAction(value: unknown): GuidanceAction | null {
  const action = asRecord(value);
  const type = String(action.type);
  if (!actionTypes.has(type)) {
    return null;
  }

  if (type === "move_camera") {
    return {
      type,
      direction: normalizeDirection(action.direction),
      strength: normalizeStrength(action.strength)
    };
  }

  const instruction = normalizeInstruction(action.instruction);
  if (!instruction) {
    return null;
  }

  if (type === "adjust_pose") {
    const poseAction: GuidanceAction = {
      type: "adjust_pose",
      instruction
    };

    if (action.strength) {
      poseAction.strength = normalizeStrength(action.strength);
    }

    return poseAction;
  }

  const framingAction: GuidanceAction = {
    type: "framing_hint",
    instruction
  };

  if (action.direction) {
    framingAction.direction = normalizeDirection(action.direction);
  }

  if (action.strength) {
    framingAction.strength = normalizeStrength(action.strength);
  }

  return framingAction;
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
    actions: actions.slice(0, 3),
    summary: typeof root.summary === "string" ? root.summary.slice(0, 80) : "",
    confidence: Math.min(1, Math.max(0, confidence))
  };

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
