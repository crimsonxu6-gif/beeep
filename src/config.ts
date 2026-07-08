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

export const appConfig = {
  sampleFps: clamp(numberFromEnv("EXPO_PUBLIC_SAMPLE_FPS", 2), 2, 5),
  aiTimeoutMs: clamp(numberFromEnv("EXPO_PUBLIC_AI_TIMEOUT_MS", 280), 120, 1200),
  shutterMuseApiUrl: process.env.EXPO_PUBLIC_SHUTTERMUSE_API_URL,
  shutterMuseBatchApiUrl: process.env.EXPO_PUBLIC_SHUTTERMUSE_BATCH_API_URL,
  stability: {
    consistentFrames: Math.round(
      clamp(numberFromEnv("EXPO_PUBLIC_STABILITY_FRAMES", 3), 2, 3)
    ),
    debounceMs: clamp(numberFromEnv("EXPO_PUBLIC_STABILITY_DEBOUNCE_MS", 450), 300, 800),
    confidenceThreshold: clamp(numberFromEnv("EXPO_PUBLIC_CONFIDENCE_THRESHOLD", 0.6), 0, 1)
  },
  pipeline: {
    batchSize: 1,
    maxBatchDelayMs: 0,
    maxQueueSize: 4
  }
} as const;
