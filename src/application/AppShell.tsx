import { useEffect, useRef, useState } from "react";
import { LayoutChangeEvent, StatusBar, StyleSheet, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";

import { AppBottomTabs } from "@/ui/AppBottomTabs";
import { AppRoute } from "./navigation";
import { appConfig } from "@/config";
import { CameraWorkspace } from "@/screens/CameraWorkspace";
import { HomeScreen } from "@/screens/HomeScreen";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { useCameraFrameSampler } from "@/camera/useCameraFrameSampler";
import { useGuidanceController } from "./useGuidanceController";
import { OverlaySize } from "@/components/GuidanceOverlay";
import { colors } from "@/theme/design";
import { CompositionMode } from "@/types/guidance";
import { useCaptureController } from "./useCaptureController";
import { PhotoPreviewScreen } from "@/screens/PhotoPreviewScreen";
import { isAutomaticAnalysisEnabled } from "./analysisState";
import { canRequestManualAnalysis } from "./analysisState";
import { CameraFacing } from "@/types/frame";

export function AppShell() {
  const cameraRef = useRef<CameraView | null>(null);
  const [route, setRoute] = useState<AppRoute>("home");
  const [permission, requestPermission] = useCameraPermissions();
  const [overlaySize, setOverlaySize] = useState<OverlaySize>({ width: 0, height: 0 });
  const [compositionMode, setCompositionMode] = useState<CompositionMode>("auto");
  const [manualCapturePending, setManualCapturePending] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<CameraFacing>("back");
  const {
    stableGuidance,
    visionFeatures,
    debugState,
    processing,
    modelStatus,
    handleFrame,
    beginAnalysis,
    cancelAnalysis,
    reset
  } = useGuidanceController(compositionMode);
  const capture = useCaptureController(cameraRef);

  const cameraActive = isAutomaticAnalysisEnabled(
    route,
    Boolean(permission?.granted),
    processing,
    capture.capturing,
    appConfig.guidanceTriggerMode
  );

  useEffect(() => {
    if (capture.photo) setRoute("photoPreview");
  }, [capture.photo]);

  useEffect(() => {
    if (route !== "camera") reset();
  }, [reset, route]);

  const frameSampler = useCameraFrameSampler({
    cameraRef,
    enabled: cameraActive,
    fps: appConfig.sampleFps,
    onFrame: handleFrame,
    captureContext: {
      cameraFacing,
      imageMirrored: cameraFacing === "front",
      previewMirrored: cameraFacing === "front",
      deviceOrientation: overlaySize.width > overlaySize.height ? "landscape_right" : "portrait",
      previewWidth: overlaySize.width,
      previewHeight: overlaySize.height
    },
    onError: (cameraError) => {
      console.warn(cameraError.message);
    }
  });

  const handleAnalyze = async () => {
    if (!canRequestManualAnalysis(
      appConfig.guidanceTriggerMode,
      processing,
      manualCapturePending,
      capture.capturing
    )) return;
    setManualCapturePending(true);
    const tapTimestamp = Date.now();
    beginAnalysis();
    const submitted = await frameSampler.captureNow(tapTimestamp);
    setManualCapturePending(false);
    if (!submitted) cancelAnalysis();
  };

  const handleLayout = (event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setOverlaySize({ width, height });
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle={route === "camera" ? "light-content" : "dark-content"} />
      {route === "home" ? <HomeScreen onNavigate={setRoute} /> : null}
      {route === "profile" ? <ProfileScreen /> : null}
      {route === "photoPreview" && capture.photo ? (
        <PhotoPreviewScreen
          photo={capture.photo}
          onRetake={() => { capture.clear(); setRoute("camera"); }}
          onSave={capture.save}
          onBack={() => { capture.clear(); setRoute("camera"); }}
          onGallery={capture.pick}
          statusMessage={capture.error}
        />
      ) : null}
      {route === "camera" ? (
        <CameraWorkspace
          cameraRef={cameraRef}
          permission={permission}
          requestPermission={requestPermission}
          overlaySize={overlaySize}
          onLayout={handleLayout}
          stableGuidance={stableGuidance}
          visionFeatures={visionFeatures}
          latencyMs={debugState.totalLatencyMs}
          processing={processing}
          modelStatus={capture.error ? {
            code: "CAMERA_ERROR",
            message: "相机暂时没有完成操作",
            suggestion: "请稍后再试",
            retryable: true,
            severity: "error"
          } : modelStatus}
          onBack={() => setRoute("home")}
          onCapture={() => { reset(); void capture.capture(); }}
          onOpenGallery={() => { reset(); void capture.pick(); }}
          capturing={capture.capturing}
          analyzing={processing || manualCapturePending}
          triggerMode={appConfig.guidanceTriggerMode}
          onAnalyze={() => { void handleAnalyze(); }}
          compositionMode={compositionMode}
          onCompositionModeChange={setCompositionMode}
          debugState={debugState}
          cameraFacing={cameraFacing}
          onToggleCamera={() => {
            reset();
            setCameraFacing((current) => current === "back" ? "front" : "back");
          }}
        />
      ) : null}
      {route !== "camera" && route !== "photoPreview" ? <AppBottomTabs activeRoute={route} onChange={setRoute} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background
  }
});
