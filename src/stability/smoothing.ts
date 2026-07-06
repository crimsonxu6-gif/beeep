import { PersonDetection, VisionFeatures } from "@/types/vision";

function smoothNumber(previous: number, next: number, alpha: number): number {
  return previous * (1 - alpha) + next * alpha;
}

function smoothPerson(previous: PersonDetection, next: PersonDetection, alpha: number): PersonDetection {
  return {
    ...next,
    bbox: [
      smoothNumber(previous.bbox[0], next.bbox[0], alpha),
      smoothNumber(previous.bbox[1], next.bbox[1], alpha),
      smoothNumber(previous.bbox[2], next.bbox[2], alpha),
      smoothNumber(previous.bbox[3], next.bbox[3], alpha)
    ]
  };
}

export class VisionSmoother {
  private previous?: VisionFeatures;

  constructor(private readonly alpha = 0.35) {}

  next(current: VisionFeatures): VisionFeatures {
    if (!this.previous) {
      this.previous = current;
      return current;
    }

    const previousById = new Map(this.previous.people.map((person) => [person.id, person]));
    const smoothed: VisionFeatures = {
      ...current,
      people: current.people.map((person) => {
        const previous = previousById.get(person.id);
        return previous ? smoothPerson(previous, person, this.alpha) : person;
      })
    };

    this.previous = smoothed;
    return smoothed;
  }
}
