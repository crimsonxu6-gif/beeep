import { expect, it } from "vitest";
import { StaleResultGuard } from "./staleResultGuard";

it("drops stale frame results", () => {
  const guard = new StaleResultGuard(1);
  guard.accept(5);
  expect(guard.shouldRender(3)).toBe(false);
  expect(guard.droppedStaleResultCount).toBe(1);
  expect(guard.shouldRender(4)).toBe(true);
});
