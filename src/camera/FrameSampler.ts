export class FrameSampler {
  private readonly minIntervalMs: number;
  private lastSampledAt = 0;

  constructor(fps: number) {
    this.minIntervalMs = 1000 / fps;
  }

  shouldSample(now = Date.now()): boolean {
    if (now - this.lastSampledAt < this.minIntervalMs) {
      return false;
    }

    this.lastSampledAt = now;
    return true;
  }
}
