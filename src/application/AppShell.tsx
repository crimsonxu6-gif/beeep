import { useRef, useState } from "react";
import {
  ActivityIndicator,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";

import { appConfig } from "@/config";
import { useCameraFrameSampler } from "@/camera/useCameraFrameSampler";
import { useGuidanceController } from "./useGuidanceController";
import { CameraOverlay, OverlaySize } from "@/ui/CameraOverlay";

export function AppShell() {
  const cameraRef = useRef<CameraView | null>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [overlaySize, setOverlaySize] = useState<OverlaySize>({ width: 0, height: 0 });
  const { stableGuidance, visionFeatures, latencyMs, processing, error, handleFrame } =
    useGuidanceController();

  useCameraFrameSampler({
    cameraRef,
    enabled: Boolean(permission?.granted),
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

  if (!permission) {
    return (
      <View style={styles.permissionScreen}>
        <ActivityIndicator color="#f8fafc" />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.permissionScreen}>
        <Text style={styles.permissionTitle}>需要相机权限</Text>
        <Pressable style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>开启相机</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.root} onLayout={handleLayout}>
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
      <CameraOverlay
        stableGuidance={stableGuidance}
        visionFeatures={visionFeatures}
        overlaySize={overlaySize}
        processing={processing}
        latencyMs={latencyMs}
        error={error}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#050505"
  },
  permissionScreen: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 18,
    padding: 24,
    backgroundColor: "#050505"
  },
  permissionTitle: {
    color: "#f8fafc",
    fontSize: 18,
    fontWeight: "700"
  },
  permissionButton: {
    minWidth: 120,
    alignItems: "center",
    borderRadius: 6,
    backgroundColor: "#f8fafc",
    paddingHorizontal: 18,
    paddingVertical: 12
  },
  permissionButtonText: {
    color: "#050505",
    fontSize: 15,
    fontWeight: "700"
  }
});
