function numberFromEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }

  const value = Number(raw);
  return Number.isFinite(value) ? value : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export type GuidanceTriggerMode = "manual" | "stable_auto" | "continuous";
export type AnalysisUploadMode = "multipart" | "base64_json";
export type AnalysisApiMode = "live" | "live_debug" | "mock_success" | "mock_error" | "mock_timeout";
export type AnalysisFixtureSource = "bundled" | "gallery";

export function guidanceTriggerModeFromEnv(value: string | undefined): GuidanceTriggerMode {
  return value === "stable_auto" || value === "continuous" ? value : "manual";
}

export function isMockEnabled(isDev: boolean, value: string | undefined): boolean {
  return isDev && value === "1";
}

export function analysisUploadModeFromEnv(value: string | undefined): AnalysisUploadMode {
  return value === "base64_json" ? "base64_json" : "multipart";
}

export function analysisApiModeFromEnv(isDev: boolean, value: string | undefined): AnalysisApiMode {
  if (!isDev) return "live";
  return value === "live_debug" || value === "mock_success" || value === "mock_error" || value === "mock_timeout"
    ? value
    : "live";
}

export function analysisFixtureEnabled(isDev: boolean, value: string | undefined): boolean {
  return isDev && value === "1";
}

export function analysisFixtureSourceFromEnv(value: string | undefined): AnalysisFixtureSource {
  return value === "gallery" ? "gallery" : "bundled";
}

const runtimeIsDev = typeof __DEV__ !== "undefined" && __DEV__;

export const appConfig = {
  debugPanel: process.env.EXPO_PUBLIC_DEBUG_PANEL === "1",
  mockEnabled: isMockEnabled(runtimeIsDev, process.env.EXPO_PUBLIC_ENABLE_MOCK),
  guidanceTriggerMode: guidanceTriggerModeFromEnv(
    process.env.EXPO_PUBLIC_GUIDANCE_TRIGGER_MODE
  ),
  enableSecondaryGuidance: process.env.EXPO_PUBLIC_ENABLE_SECONDARY_GUIDANCE === "1",
  analysisImageShortEdge: Math.round(
    clamp(numberFromEnv("EXPO_PUBLIC_ANALYSIS_IMAGE_SHORT_EDGE", 768), 320, 1600)
  ),
  analysisJpegQuality: clamp(
    numberFromEnv("EXPO_PUBLIC_ANALYSIS_JPEG_QUALITY", 0.7), 0.4, 1
  ),
  analysisUploadMode: analysisUploadModeFromEnv(
    process.env.EXPO_PUBLIC_ANALYSIS_UPLOAD_MODE
  ),
  analysisApiMode: analysisApiModeFromEnv(
    runtimeIsDev,
    process.env.EXPO_PUBLIC_ANALYSIS_API_MODE
  ),
  analysisFixtureEnabled: analysisFixtureEnabled(
    runtimeIsDev,
    process.env.EXPO_PUBLIC_ENABLE_ANALYSIS_FIXTURE
  ),
  analysisFixtureSource: analysisFixtureSourceFromEnv(
    process.env.EXPO_PUBLIC_ANALYSIS_FIXTURE_SOURCE
  ),
  sampleFps: clamp(numberFromEnv("EXPO_PUBLIC_SAMPLE_FPS", 0.75), 0.5, 1),
  visionTimeoutMs: clamp(numberFromEnv("EXPO_PUBLIC_VISION_TIMEOUT_MS", 1000), 250, 5000),
  guidanceTimeoutMs: clamp(numberFromEnv("EXPO_PUBLIC_GUIDANCE_TIMEOUT_MS", 19000), 500, 30000),
  analyzeApiUrl: process.env.EXPO_PUBLIC_ANALYZE_API_URL,
  analysisDebugApiUrl: process.env.EXPO_PUBLIC_ANALYSIS_DEBUG_API_URL,
  shutterMuseApiUrl: process.env.EXPO_PUBLIC_SHUTTERMUSE_API_URL,
  stability: {
    consistentFrames: Math.round(
      clamp(numberFromEnv("EXPO_PUBLIC_STABILITY_FRAMES", 3), 2, 3)
    ),
    debounceMs: clamp(numberFromEnv("EXPO_PUBLIC_STABILITY_DEBOUNCE_MS", 1800), 800, 3000),
    confidenceThreshold: clamp(numberFromEnv("EXPO_PUBLIC_CONFIDENCE_THRESHOLD", 0.6), 0, 1),
    expiresMs: clamp(numberFromEnv("EXPO_PUBLIC_GUIDANCE_EXPIRES_MS", 2500), 1000, 5000)
  },
  pipeline: {
    allowedFrameLag: 1
  }
} as const;
