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

export function isMockEnabled(isDev: boolean, value: string | undefined): boolean {
  return isDev && value === "1";
}

const runtimeIsDev = typeof __DEV__ !== "undefined" && __DEV__;

export const appConfig = {
  debugPanel: process.env.EXPO_PUBLIC_DEBUG_PANEL === "1",
  mockEnabled: isMockEnabled(runtimeIsDev, process.env.EXPO_PUBLIC_ENABLE_MOCK),
  sampleFps: clamp(numberFromEnv("EXPO_PUBLIC_SAMPLE_FPS", 0.75), 0.5, 1),
  visionTimeoutMs: clamp(numberFromEnv("EXPO_PUBLIC_VISION_TIMEOUT_MS", 1000), 250, 5000),
  guidanceTimeoutMs: clamp(numberFromEnv("EXPO_PUBLIC_GUIDANCE_TIMEOUT_MS", 5000), 500, 15000),
  analyzeApiUrl: process.env.EXPO_PUBLIC_ANALYZE_API_URL,
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
