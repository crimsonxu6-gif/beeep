import { StyleSheet, View } from "react-native";
import Svg, { Line } from "react-native-svg";

import { StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { appConfig } from "@/config";
import { GuidanceDebugPanel } from "./GuidanceDebugPanel";
import { guidanceToInstruction } from "@/ui/instructionFormatter";
import { InstructionText } from "@/ui/InstructionText";
import { OverlayArrows } from "@/ui/OverlayArrows";
import { stableGuidanceVariant } from "@/ui/guidanceVisuals";
import { GuidanceDebugState } from "@/ai_engine/guidancePipeline";
import { CompositionMode } from "@/types/guidance";
import { CompositionBoxOverlay } from "./CompositionBoxOverlay";
import { PoseSkeletonOverlay } from "./PoseSkeletonOverlay";

export interface OverlaySize {
  width: number;
  height: number;
}

interface GuidanceOverlayProps {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  overlaySize: OverlaySize;
  processing: boolean;
  latencyMs: number | null;
  error: string | null;
  debugState: GuidanceDebugState;
  compositionMode: CompositionMode;
}

function RuleOfThirdsGrid({ width, height }: OverlaySize) {
  if (width <= 0 || height <= 0) {
    return null;
  }

  const x1 = width / 3;
  const x2 = (width * 2) / 3;
  const y1 = height / 3;
  const y2 = (height * 2) / 3;

  return (
    <Svg pointerEvents="none" style={StyleSheet.absoluteFill} width={width} height={height}>
      {[x1, x2].map((x) => (
        <Line
          key={`v-${x}`}
          x1={x}
          y1={0}
          x2={x}
          y2={height}
          stroke="rgba(255,255,255,0.34)"
          strokeWidth={0.7}
        />
      ))}
      {[y1, y2].map((y) => (
        <Line
          key={`h-${y}`}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke="rgba(255,255,255,0.3)"
          strokeWidth={0.7}
        />
      ))}
    </Svg>
  );
}

export function GuidanceOverlay({
  stableGuidance,
  visionFeatures,
  overlaySize,
  processing,
  latencyMs,
  error,
  debugState,
  compositionMode
}: GuidanceOverlayProps) {
  const guidance = stableGuidance?.guidance;
  const instruction = guidanceToInstruction(guidance);
  const visualVariant = stableGuidanceVariant(stableGuidance?.key);

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <RuleOfThirdsGrid width={overlaySize.width} height={overlaySize.height} />
      <CompositionBoxOverlay guidance={guidance} size={overlaySize} />
      <PoseSkeletonOverlay guidance={guidance} size={overlaySize} />
      <OverlayArrows guidance={guidance} variant={visualVariant} />
      <InstructionText
        text={instruction}
        processing={processing}
        latencyMs={latencyMs}
        error={error}
        variant={visualVariant}
      />
      {appConfig.debugPanel ? (
        <GuidanceDebugPanel
          stableGuidance={stableGuidance}
          visionFeatures={visionFeatures}
          latencyMs={latencyMs}
          processing={processing}
          debugState={debugState}
          compositionMode={compositionMode}
        />
      ) : null}
    </View>
  );
}
