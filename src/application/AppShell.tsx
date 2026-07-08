import { useRef, useState } from "react";
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

export function AppShell() {
  const cameraRef = useRef<CameraView | null>(null);
  const [route, setRoute] = useState<AppRoute>("camera");
  const [permission, requestPermission] = useCameraPermissions();
  const [overlaySize, setOverlaySize] = useState<OverlaySize>({ width: 0, height: 0 });
  const { stableGuidance, visionFeatures, latencyMs, processing, error, handleFrame } =
    useGuidanceController();

  const cameraActive = route === "camera" && Boolean(permission?.granted);

  useCameraFrameSampler({
    cameraRef,
    enabled: cameraActive,
    fps: appConfig.sampleFps,
    onFrame: handleFrame,
    onError: (cameraError) => {
      console.warn(cameraError.message);
    }
  });

  const handleLayout = (event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setOverlaySize({ width, height });
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle={route === "camera" ? "light-content" : "dark-content"} />
      {route === "home" ? <HomeScreen onNavigate={setRoute} /> : null}
      {route === "profile" ? <ProfileScreen /> : null}
      {route === "camera" ? (
        <CameraWorkspace
          cameraRef={cameraRef}
          permission={permission}
          requestPermission={requestPermission}
          overlaySize={overlaySize}
          onLayout={handleLayout}
          stableGuidance={stableGuidance}
          visionFeatures={visionFeatures}
          latencyMs={latencyMs}
          processing={processing}
          error={error}
          onBack={() => setRoute("home")}
        />
      ) : null}
      {route !== "camera" ? <AppBottomTabs activeRoute={route} onChange={setRoute} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background
  }
});
