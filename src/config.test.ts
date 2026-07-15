import { expect, it } from "vitest";
import {
  analysisUploadModeFromEnv,
  guidanceTriggerModeFromEnv,
  isMockEnabled
} from "./config";

it("never enables mock in production", () => {
  expect(isMockEnabled(false, "1")).toBe(false);
  expect(isMockEnabled(true, "1")).toBe(true);
});

it("defaults analysis uploads to multipart", () => {
  expect(analysisUploadModeFromEnv(undefined)).toBe("multipart");
  expect(analysisUploadModeFromEnv("multipart")).toBe("multipart");
  expect(analysisUploadModeFromEnv("base64_json")).toBe("base64_json");
});

it("defaults guidance triggering to manual mode", () => {
  expect(guidanceTriggerModeFromEnv(undefined)).toBe("manual");
  expect(guidanceTriggerModeFromEnv("invalid")).toBe("manual");
  expect(guidanceTriggerModeFromEnv("stable_auto")).toBe("stable_auto");
  expect(guidanceTriggerModeFromEnv("continuous")).toBe("continuous");
});
