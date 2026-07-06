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
        <View style={[styles.gridLine, styles.v1]} />
        <View style={[styles.gridLine, styles.v2]} />
        <View style={[styles.gridLine, styles.h1]} />
        <View style={[styles.gridLine, styles.h2]} />
      </View>
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
    opacity: 0.34
  },
  gridLine: {
    position: "absolute",
    backgroundColor: "rgba(255,255,255,0.34)"
  },
  v1: {
    left: "33.333%",
    top: 0,
    bottom: 0,
    width: 1
  },
  v2: {
    left: "66.666%",
    top: 0,
    bottom: 0,
    width: 1
  },
  h1: {
    top: "33.333%",
    left: 0,
    right: 0,
    height: 1
  },
  h2: {
    top: "66.666%",
    left: 0,
    right: 0,
    height: 1
  }
});
