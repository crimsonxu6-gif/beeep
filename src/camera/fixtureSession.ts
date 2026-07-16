import {
  AnalysisApiMode,
  AnalysisFailureScenario,
  AnalysisUploadMode,
  CameraFacing,
  DeviceOrientation,
  SimulatedNetworkProfile
} from "@/types/frame";

export const FIXTURE_PREVIEW_RATIOS = ["9:16", "3:4", "4:3", "16:9", "1:1"] as const;
export type FixturePreviewRatio = typeof FIXTURE_PREVIEW_RATIOS[number];

export const FIXTURE_DEVICE_PRESETS = [
  { id: "android_mid", label: "1080 x 1920", width: 1080, height: 1920 },
  { id: "iphone", label: "1170 x 2532", width: 1170, height: 2532 },
  { id: "android_large", label: "1440 x 3200", width: 1440, height: 3200 },
  { id: "android_low", label: "720 x 1600", width: 720, height: 1600 }
] as const;

export interface FixtureSessionSettings {
  fixtureId: string;
  cameraFacing: CameraFacing;
  imageMirrored: boolean;
  deviceOrientation: DeviceOrientation;
  previewRatio: FixturePreviewRatio;
  devicePresetId: string;
  uploadMode: AnalysisUploadMode;
  apiMode: AnalysisApiMode;
  networkProfile: SimulatedNetworkProfile;
  failureScenario: AnalysisFailureScenario;
}

export const DEFAULT_FIXTURE_SETTINGS: FixtureSessionSettings = {
  fixtureId: "front_portrait",
  cameraFacing: "back",
  imageMirrored: false,
  deviceOrientation: "portrait",
  previewRatio: "9:16",
  devicePresetId: "android_mid",
  uploadMode: "multipart",
  apiMode: "mock_success",
  networkProfile: "normal",
  failureScenario: "invalid_model_output"
};

export function previewAspectRatio(value: FixturePreviewRatio, orientation: DeviceOrientation): number {
  void orientation;
  const [first, second] = value.split(":").map(Number);
  return (first ?? 9) / (second ?? 16);
}

export function simulatedPreviewSize(settings: FixtureSessionSettings): { width: number; height: number } {
  const preset = FIXTURE_DEVICE_PRESETS.find((item) => item.id === settings.devicePresetId)
    ?? FIXTURE_DEVICE_PRESETS[0];
  const portraitWidth = Math.min(preset.width, preset.height);
  const portraitHeight = Math.max(preset.width, preset.height);
  const ratio = previewAspectRatio(settings.previewRatio, settings.deviceOrientation);
  const maxWidth = settings.deviceOrientation.startsWith("landscape") ? portraitHeight : portraitWidth;
  const maxHeight = settings.deviceOrientation.startsWith("landscape") ? portraitWidth : portraitHeight;
  const width = Math.min(maxWidth, Math.round(maxHeight * ratio));
  return { width, height: Math.round(width / ratio) };
}
