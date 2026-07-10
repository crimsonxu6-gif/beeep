import { GuidanceAction, GuidanceOutput, StableGuidance } from "@/types/guidance";

interface StabilityFilterOptions {
  consistentFrames: number;
  confidenceThreshold: number;
  debounceMs: number;
  expiresMs: number;
}

function actionSignature(action: GuidanceAction): string {
  if (action.type === "adjust_distance" || action.type === "adjust_angle") {
    return `${action.type}:${action.direction}`;
  }
  if (action.type === "move_camera") {
    return `${action.type}:${action.direction}`;
  }
  return action.type;
}

function guidanceSignature(guidance: GuidanceOutput): string {
  if (guidance.actions.length === 0) {
    return "empty";
  }

  return `${guidance.problem?.type ?? "none"}|${guidance.actions.map(actionSignature).join("|")}`;
}

export class StabilityFilter {
  private history: Array<{ key: string; guidance: GuidanceOutput }> = [];
  private lastPublishedKey: string | undefined;
  private lastPublishedAt = 0;

  constructor(private readonly options: StabilityFilterOptions) {}

  next(guidance: GuidanceOutput, now = Date.now()): StableGuidance | null {
    if (guidance.confidence < this.options.confidenceThreshold) {
      return null;
    }

    const key = guidanceSignature(guidance);
    this.history = [...this.history, { key, guidance }].slice(-this.options.consistentFrames);

    const isConsistent =
      this.history.length === this.options.consistentFrames &&
      this.history.every((item) => item.key === key);
    const debounceElapsed = now - this.lastPublishedAt >= this.options.debounceMs;
    const changed = key !== this.lastPublishedKey;
    const refreshDue = now - this.lastPublishedAt >= this.options.expiresMs;

    if (!isConsistent || !debounceElapsed || (!changed && !refreshDue)) {
      return null;
    }

    this.lastPublishedKey = key;
    this.lastPublishedAt = now;

    return {
      key,
      guidance,
      updatedAt: now
    };
  }

  isExpired(now = Date.now()): boolean {
    return this.lastPublishedAt > 0 && now - this.lastPublishedAt >= this.options.expiresMs;
  }

  reset(): void {
    this.history = [];
    this.lastPublishedKey = undefined;
    this.lastPublishedAt = 0;
  }
}
