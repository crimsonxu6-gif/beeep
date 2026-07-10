import { expect, it } from "vitest";
import { isMockEnabled } from "./config";

it("never enables mock in production", () => {
  expect(isMockEnabled(false, "1")).toBe(false);
  expect(isMockEnabled(true, "1")).toBe(true);
});
