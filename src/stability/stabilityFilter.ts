import { GuidanceAction, GuidanceOutput, StableGuidance } from "@/types/guidance";

interface StabilityFilterOptions {
  consistentFrames: number;
  confidenceThreshold: number;
  debounceMs: number;
}

function actionSignature(action: GuidanceAction): string {
  if (action.type === "move_camera") {
    return `${action.type}:${action.direction}:${action.strength}`;
  }

  return `${action.type}:${action.instruction.toLowerCase().trim()}:${action.strength ?? "medium"}`;
}

function guidanceSignature(guidance: GuidanceOutput): string {
  if (guidance.actions.length === 0) {
    return "empty";
  }

  return guidance.actions.map(actionSignature).join("|");
}

export class StabilityFilter {
  private candidateKey?: string;
  private candidateGuidance?: GuidanceOutput;
  private candidateCount = 0;
  private lastPublishedKey?: string;
  private lastPublishedAt = 0;

  constructor(private readonly options: StabilityFilterOptions) {}

  next(guidance: GuidanceOutput, now = Date.now()): StableGuidance | null {
    if (guidance.confidence < this.options.confidenceThreshold) {
      return null;
    }

    const key = guidanceSignature(guidance);
    if (key === this.candidateKey) {
      this.candidateCount += 1;
    } else {
      this.candidateKey = key;
      this.candidateGuidance = guidance;
      this.candidateCount = 1;
    }

    const isConsistent = this.candidateCount >= this.options.consistentFrames;
    const debounceElapsed = now - this.lastPublishedAt >= this.options.debounceMs;
    const changed = key !== this.lastPublishedKey;

    if (!isConsistent || !debounceElapsed || !changed || !this.candidateGuidance) {
      return null;
    }

    this.lastPublishedKey = key;
    this.lastPublishedAt = now;

    return {
      key,
      guidance: this.candidateGuidance,
      updatedAt: now
    };
  }
}
