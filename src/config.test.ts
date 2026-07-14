import { expect, it } from "vitest";
import { guidanceTriggerModeFromEnv, isMockEnabled } from "./config";

it("never enables mock in production", () => {
  expect(isMockEnabled(false, "1")).toBe(false);
  expect(isMockEnabled(true, "1")).toBe(true);
});

it("defaults guidance triggering to manual mode", () => {
  expect(guidanceTriggerModeFromEnv(undefined)).toBe("manual");
  expect(guidanceTriggerModeFromEnv("invalid")).toBe("manual");
  expect(guidanceTriggerModeFromEnv("stable_auto")).toBe("stable_auto");
  expect(guidanceTriggerModeFromEnv("continuous")).toBe("continuous");
});
