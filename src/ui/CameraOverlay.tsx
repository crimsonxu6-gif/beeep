import { StyleSheet, View } from "react-native";

import { StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { guidanceToInstruction } from "./instructionFormatter";
import { InstructionText } from "./InstructionText";
import { OverlayArrows } from "./OverlayArrows";
import { PersonBoxOverlay } from "./PersonBoxOverlay";

export interface OverlaySize {
  width: number;
  height: number;
}

interface CameraOverlayProps {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  overlaySize: OverlaySize;
  processing: boolean;
  latencyMs: number | null;
  error: string | null;
}

export function CameraOverlay({
  stableGuidance,
  visionFeatures,
  overlaySize,
  processing,
  latencyMs,
  error
}: CameraOverlayProps) {
  const guidance = stableGuidance?.guidance;
  const instruction = guidanceToInstruction(guidance);

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <View style={styles.ruleOfThirds}>
        <View style={[styles.verticalLine, styles.v1]} />
        <View style={[styles.verticalLine, styles.v2]} />
        <View style={[styles.horizontalLine, styles.h1]} />
        <View style={[styles.horizontalLine, styles.h2]} />
      </View>
      <View style={styles.doodleMarkA} />
      <View style={styles.doodleMarkB} />
      <PersonBoxOverlay visionFeatures={visionFeatures} overlaySize={overlaySize} />
      <OverlayArrows guidance={guidance} />
      <InstructionText text={instruction} processing={processing} latencyMs={latencyMs} error={error} />
    </View>
  );
}

const styles = StyleSheet.create({
  ruleOfThirds: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    opacity: 0.38
  },
  verticalLine: {
    position: "absolute",
    top: 118,
    bottom: 160,
    width: 0,
    borderLeftWidth: 1,
    borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.72)"
  },
  horizontalLine: {
    position: "absolute",
    left: 26,
    right: 26,
    height: 0,
    borderTopWidth: 1,
    borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.72)"
  },
  v1: {
    left: "33.333%",
    transform: [{ rotate: "-0.6deg" }]
  },
  v2: {
    left: "66.666%",
    transform: [{ rotate: "0.5deg" }]
  },
  h1: {
    top: "38%",
    transform: [{ rotate: "0.4deg" }]
  },
  h2: {
    top: "64%",
    transform: [{ rotate: "-0.4deg" }]
  },
  doodleMarkA: {
    position: "absolute",
    left: 28,
    top: 142,
    width: 28,
    height: 18,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    borderColor: "rgba(255,255,255,0.55)",
    transform: [{ rotate: "-22deg" }]
  },
  doodleMarkB: {
    position: "absolute",
    right: 28,
    bottom: 262,
    width: 30,
    height: 18,
    borderRightWidth: 2,
    borderTopWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    transform: [{ rotate: "18deg" }]
  }
});
