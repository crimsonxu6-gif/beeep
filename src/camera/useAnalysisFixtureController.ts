import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { File } from "expo-file-system";

import { AnalysisFrameController } from "./AnalysisFrameController";
import {
  ANALYSIS_FIXTURES,
  AnalysisFixture,
  bundledFixtureSource,
  galleryFixtureSource
} from "./analysisFixtures";
import {
  DEFAULT_FIXTURE_SETTINGS,
  FixtureSessionSettings,
  simulatedPreviewSize
} from "./fixtureSession";
import { CapturedFrame, AnalysisSourceFrame } from "@/types/frame";
import { AnalysisFixtureSource } from "@/config";

export function useAnalysisFixtureController(
  enabled: boolean,
  initialSource: AnalysisFixtureSource = "bundled"
) {
  const [settings, setSettings] = useState<FixtureSessionSettings>(DEFAULT_FIXTURE_SETTINGS);
  const [source, setSource] = useState<AnalysisSourceFrame | null>(null);
  const [processedPreviewUri, setProcessedPreviewUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceKind, setSourceKind] = useState<AnalysisFixtureSource>(initialSource);
  const controllerRef = useRef(new AnalysisFrameController());
  const frameIdRef = useRef(100_000);

  const selectedFixture = useMemo(
    () => ANALYSIS_FIXTURES.find((item) => item.id === settings.fixtureId) ?? ANALYSIS_FIXTURES[0]!,
    [settings.fixtureId]
  );

  const loadBundled = useCallback(async (fixture: AnalysisFixture, next = settings) => {
    try {
      const resolved = await bundledFixtureSource(fixture, {
        cameraFacing: next.cameraFacing,
        imageMirrored: next.imageMirrored,
        previewMirrored: next.cameraFacing === "front",
        deviceOrientation: next.deviceOrientation
      });
      setSource(resolved);
      setProcessedPreviewUri(null);
      setError(null);
    } catch (fixtureError) {
      setError(fixtureError instanceof Error ? fixtureError.message : String(fixtureError));
    }
  }, [settings]);

  useEffect(() => {
    if (!enabled || sourceKind !== "bundled") return;
    void loadBundled(selectedFixture, settings);
  }, [enabled, loadBundled, selectedFixture, settings, sourceKind]);

  const updateSettings = useCallback((patch: Partial<FixtureSessionSettings>) => {
    if (patch.fixtureId) setSourceKind("bundled");
    setSettings((current) => ({ ...current, ...patch }));
  }, []);

  const pickGallery = useCallback(async () => {
    const ImagePicker = await import("expo-image-picker");
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError("需要图库权限");
      return false;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 1,
      allowsEditing: false
    });
    const asset = result.assets?.[0];
    if (result.canceled || !asset) return false;
    setSource(galleryFixtureSource(asset, {
      cameraFacing: settings.cameraFacing,
      imageMirrored: settings.imageMirrored,
      previewMirrored: settings.cameraFacing === "front",
      deviceOrientation: settings.deviceOrientation
    }));
    setSourceKind("gallery");
    setProcessedPreviewUri(null);
    setError(null);
    return true;
  }, [settings]);

  const captureNow = useCallback(async (tapTimestamp: number): Promise<CapturedFrame | null> => {
    if (!source) return null;
    const preview = simulatedPreviewSize(settings);
    const captureStartedAt = Date.now();
    await new File(source.uri).bytes();
    const captureCompletedAt = Date.now();
    const frame = await controllerRef.current.processAnalysisSourceFrame(
      {
        ...source,
        cameraFacing: settings.cameraFacing,
        imageMirrored: settings.imageMirrored,
        previewMirrored: settings.cameraFacing === "front",
        deviceOrientation: settings.deviceOrientation,
        captureStartedAt,
        captureCompletedAt
      },
      frameIdRef.current++,
      {
        tapTimestamp,
        cameraFacing: settings.cameraFacing,
        imageMirrored: settings.imageMirrored,
        previewMirrored: settings.cameraFacing === "front",
        deviceOrientation: settings.deviceOrientation,
        previewWidth: preview.width,
        previewHeight: preview.height,
        apiMode: settings.apiMode,
        uploadMode: settings.uploadMode,
        networkProfile: settings.networkProfile,
        failureScenario: settings.failureScenario
      }
    );
    setProcessedPreviewUri(frame.image.uri ?? null);
    if (__DEV__) {
      console.info("BEEEP_FIXTURE_PREPROCESS", JSON.stringify({
        fixtureId: sourceKind === "bundled" ? selectedFixture.id : "gallery",
        source: source.source,
        sourceWidth: frame.image.originalWidth,
        sourceHeight: frame.image.originalHeight,
        processedWidth: frame.image.width,
        processedHeight: frame.image.height,
        sourceBytes: frame.image.originalBytes,
        processedImageBytes: frame.image.processedImageBytes,
        preprocessMs: frame.capture
          ? frame.capture.preprocessCompletedAt - frame.capture.captureCompletedAt
          : null,
        outputUri: frame.image.uri,
        mimeType: frame.image.mimeType
      }));
    }
    return frame;
  }, [selectedFixture.id, settings, source, sourceKind]);

  const clear = useCallback(() => {
    setProcessedPreviewUri(null);
    setError(null);
  }, []);

  return {
    settings,
    updateSettings,
    fixtures: ANALYSIS_FIXTURES,
    selectedFixture,
    sourceKind,
    source,
    previewUri: processedPreviewUri ?? source?.uri ?? null,
    processedPreviewUri,
    error,
    captureNow,
    pickGallery,
    clear
  };
}
