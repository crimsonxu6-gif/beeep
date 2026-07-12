import { RefObject } from "react";
import {
  ActivityIndicator,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View
} from "react-native";
import { CameraView, PermissionResponse } from "expo-camera";
import { Aperture, Camera, ChevronLeft, Images } from "lucide-react-native";

import { GuidanceOverlay, OverlaySize } from "@/components/GuidanceOverlay";
import { ModelStatus, StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { colors, radii, typography } from "@/theme/design";
import { CompositionMode } from "@/types/guidance";
import { GuidanceDebugState } from "@/ai_engine/guidancePipeline";

interface CameraWorkspaceProps {
  cameraRef: RefObject<CameraView | null>;
  permission: PermissionResponse | null;
  requestPermission: () => void;
  overlaySize: OverlaySize;
  onLayout: (event: LayoutChangeEvent) => void;
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  latencyMs: number | null;
  processing: boolean;
  modelStatus: ModelStatus | null;
  onBack: () => void;
  onCapture: () => void;
  onOpenGallery: () => void;
  capturing: boolean;
  compositionMode: CompositionMode;
  onCompositionModeChange: (mode: CompositionMode) => void;
  debugState: GuidanceDebugState;
}

export function CameraWorkspace({
  cameraRef,
  permission,
  requestPermission,
  overlaySize,
  onLayout,
  stableGuidance,
  visionFeatures,
  latencyMs,
  processing,
  modelStatus,
  onBack,
  onCapture,
  onOpenGallery,
  capturing,
  compositionMode,
  onCompositionModeChange,
  debugState
}: CameraWorkspaceProps) {
  const granted = Boolean(permission?.granted);

  return (
    <View style={styles.root} onLayout={onLayout}>
      {granted ? (
        <>
          <CameraView
            ref={cameraRef}
            style={StyleSheet.absoluteFill}
            facing="back"
            flash="off"
            enableTorch={false}
            animateShutter={false}
          />
          <GuidanceOverlay
            stableGuidance={stableGuidance}
            visionFeatures={visionFeatures}
            overlaySize={overlaySize}
            processing={processing}
            latencyMs={latencyMs}
            modelStatus={modelStatus}
            debugState={debugState}
            compositionMode={compositionMode}
          />
        </>
      ) : (
        <View style={styles.permissionSurface}>
          {!permission ? <ActivityIndicator color={colors.text} /> : null}
          <Text style={styles.permissionTitle}>需要相机权限</Text>
          <Pressable style={styles.permissionButton} onPress={requestPermission}>
            <Camera size={18} strokeWidth={2.3} color={colors.white} />
            <Text style={styles.permissionText}>开启相机</Text>
          </Pressable>
        </View>
      )}

      <View style={styles.topBar}>
        <Pressable style={styles.topIcon} onPress={onBack}>
          <ChevronLeft size={22} strokeWidth={2.4} color={colors.white} />
        </Pressable>
        <View style={styles.topTitleWrap}>
          <Text style={styles.topTitle}>实时构图</Text>
          <Text style={styles.topMeta}>
            {modelStatus
              ? modelStatus.severity === "waiting" ? "AI 准备中" : "AI 暂不可用"
              : processing ? "分析中" : "Ready"}
          </Text>
        </View>
        <View style={styles.topSpacer} />
      </View>

      <View style={styles.modeRail}>
        <View style={styles.modePill}>
          <Aperture size={16} strokeWidth={2.2} color={colors.white} />
          <Text style={styles.modeText}>{compositionMode === "auto" ? "自动构图" : compositionMode === "thirds_left" ? "左三分" : compositionMode === "thirds_right" ? "右三分" : "居中"}</Text>
        </View>
        <View style={styles.modeChoices}>
          {(["auto", "center", "thirds_left", "thirds_right"] as const).map((mode) => (
            <Pressable key={mode} style={[styles.modeDot, mode === compositionMode && styles.modeDotActive]} onPress={() => onCompositionModeChange(mode)} />
          ))}
        </View>
      </View>

      <View style={styles.captureDock}>
        <Pressable style={styles.sideControl} onPress={onOpenGallery}>
          <Images size={22} strokeWidth={2.2} color={colors.white} />
          <Text style={styles.sideControlText}>图库</Text>
        </Pressable>
        <Pressable style={[styles.shutter, capturing && styles.shutterDisabled]} onPress={onCapture} disabled={capturing}>
          <View style={styles.shutterInner} />
        </Pressable>
        <View style={styles.dockSpacer} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    overflow: "hidden",
    backgroundColor: colors.cameraInk
  },
  permissionSurface: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    backgroundColor: colors.background
  },
  permissionTitle: {
    ...typography.section,
    color: colors.text
  },
  permissionButton: {
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: radii.md,
    backgroundColor: colors.text,
    paddingHorizontal: 16
  },
  permissionText: {
    ...typography.body,
    color: colors.white,
    fontWeight: "800"
  },
  topBar: {
    position: "absolute",
    left: 16,
    right: 16,
    top: 54,
    height: 48,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: radii.md,
    backgroundColor: colors.cameraPanel,
    paddingHorizontal: 8
  },
  topIcon: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.round,
    backgroundColor: "rgba(255,255,255,0.12)"
  },
  topSpacer: {
    width: 36,
    height: 36
  },
  topTitleWrap: {
    alignItems: "center"
  },
  topTitle: {
    ...typography.body,
    color: colors.white,
    fontWeight: "800"
  },
  topMeta: {
    ...typography.caption,
    color: "rgba(255,255,255,0.68)"
  },
  modeRail: {
    position: "absolute",
    right: 14,
    bottom: 176,
    gap: 8
  },
  modePill: {
    minHeight: 36,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    borderRadius: radii.md,
    backgroundColor: colors.cameraPanel,
    paddingHorizontal: 10
  },
  modeText: {
    ...typography.caption,
    color: colors.white
  },
  modeChoices: { alignItems: "center", gap: 7, paddingVertical: 8 },
  modeDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: "rgba(255,255,255,0.38)" },
  modeDotActive: { width: 18, backgroundColor: colors.white },
  captureDock: {
    position: "absolute",
    left: 22,
    right: 22,
    bottom: 92,
    height: 78,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: radii.md,
    backgroundColor: colors.cameraPanel,
    paddingHorizontal: 22
  },
  sideControl: {
    width: 64,
    alignItems: "center",
    justifyContent: "center",
    gap: 4
  },
  sideControlText: {
    ...typography.caption,
    color: "rgba(255,255,255,0.76)"
  },
  dockSpacer: {
    width: 64,
    height: 44
  },
  shutter: {
    width: 62,
    height: 62,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.round,
    borderWidth: 3,
    borderColor: colors.white
  },
  shutterInner: {
    width: 46,
    height: 46,
    borderRadius: radii.round,
    backgroundColor: colors.white
  },
  shutterDisabled: { opacity: 0.5 }
});
