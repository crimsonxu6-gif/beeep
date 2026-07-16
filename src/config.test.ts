import { expect, it } from "vitest";
import {
  analysisApiModeFromEnv,
  analysisFixtureEnabled,
  analysisFixtureSourceFromEnv,
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

it("keeps fixture and mock API modes disabled in production", () => {
  expect(analysisFixtureEnabled(false, "1")).toBe(false);
  expect(analysisFixtureEnabled(true, "1")).toBe(true);
  expect(analysisApiModeFromEnv(false, "mock_success")).toBe("live");
  expect(analysisApiModeFromEnv(false, "live_debug")).toBe("live");
  expect(analysisApiModeFromEnv(true, "live_debug")).toBe("live_debug");
  expect(analysisApiModeFromEnv(true, "mock_success")).toBe("mock_success");
  expect(analysisApiModeFromEnv(true, "invalid")).toBe("live");
  expect(analysisFixtureSourceFromEnv("gallery")).toBe("gallery");
  expect(analysisFixtureSourceFromEnv(undefined)).toBe("bundled");
});

it("defaults guidance triggering to manual mode", () => {
  expect(guidanceTriggerModeFromEnv(undefined)).toBe("manual");
  expect(guidanceTriggerModeFromEnv("invalid")).toBe("manual");
  expect(guidanceTriggerModeFromEnv("stable_auto")).toBe("stable_auto");
  expect(guidanceTriggerModeFromEnv("continuous")).toBe("continuous");
});
