export class StaleResultGuard {
  latestAcceptedFrameId = 0;
  latestProcessedFrameId = 0;
  latestRenderedFrameId = 0;
  droppedStaleResultCount = 0;

  constructor(private readonly allowedLag = 1) {}

  accept(frameId: number): void {
    this.latestAcceptedFrameId = Math.max(this.latestAcceptedFrameId, frameId);
  }

  shouldRender(frameId: number): boolean {
    this.latestProcessedFrameId = Math.max(this.latestProcessedFrameId, frameId);
    if (frameId < this.latestAcceptedFrameId - this.allowedLag) {
      this.droppedStaleResultCount += 1;
      return false;
    }
    this.latestRenderedFrameId = Math.max(this.latestRenderedFrameId, frameId);
    return true;
  }

  reset(): void {
    this.latestAcceptedFrameId = 0;
    this.latestProcessedFrameId = 0;
    this.latestRenderedFrameId = 0;
    this.droppedStaleResultCount = 0;
  }
}
