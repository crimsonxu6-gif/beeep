import { StyleSheet, View } from "react-native";
import Svg, { Path } from "react-native-svg";

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

function DoodleGuides({ width, height }: OverlaySize) {
  if (width <= 0 || height <= 0) {
    return null;
  }

  const top = 120;
  const bottom = height - 168;
  const left = 28;
  const right = width - 28;
  const x1 = width * 0.34;
  const x2 = width * 0.66;
  const y1 = height * 0.38;
  const y2 = height * 0.64;

  return (
    <Svg pointerEvents="none" style={StyleSheet.absoluteFill} width={width} height={height}>
      <Path
        d={`M ${x1} ${top} C ${x1 - 10} ${height * 0.32}, ${x1 + 9} ${height * 0.52}, ${x1 - 4} ${bottom}`}
        stroke="rgba(255,255,255,0.52)"
        strokeWidth={1.2}
        strokeLinecap="round"
        strokeDasharray="8 13"
        fill="none"
      />
      <Path
        d={`M ${x2} ${top + 6} C ${x2 + 8} ${height * 0.34}, ${x2 - 7} ${height * 0.52}, ${x2 + 5} ${bottom}`}
        stroke="rgba(255,255,255,0.46)"
        strokeWidth={1.2}
        strokeLinecap="round"
        strokeDasharray="7 14"
        fill="none"
      />
      <Path
        d={`M ${left} ${y1} C ${width * 0.28} ${y1 - 8}, ${width * 0.62} ${y1 + 7}, ${right} ${y1 - 3}`}
        stroke="rgba(255,255,255,0.5)"
        strokeWidth={1.2}
        strokeLinecap="round"
        strokeDasharray="9 14"
        fill="none"
      />
      <Path
        d={`M ${left + 10} ${y2} C ${width * 0.32} ${y2 + 7}, ${width * 0.7} ${y2 - 8}, ${right - 8} ${y2 + 2}`}
        stroke="rgba(255,255,255,0.45)"
        strokeWidth={1.2}
        strokeLinecap="round"
        strokeDasharray="8 13"
        fill="none"
      />
      <Path
        d={`M 28 146 C 38 132, 50 134, 58 147`}
        stroke="rgba(255,255,255,0.42)"
        strokeWidth={2}
        strokeLinecap="round"
        fill="none"
      />
      <Path
        d={`M ${width - 60} ${height - 270} C ${width - 46} ${height - 282}, ${width - 34} ${height - 276}, ${width - 26} ${height - 260}`}
        stroke="rgba(255,255,255,0.38)"
        strokeWidth={2}
        strokeLinecap="round"
        fill="none"
      />
    </Svg>
  );
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
      <DoodleGuides width={overlaySize.width} height={overlaySize.height} />
      <PersonBoxOverlay visionFeatures={visionFeatures} overlaySize={overlaySize} />
      <OverlayArrows guidance={guidance} />
      <InstructionText text={instruction} processing={processing} latencyMs={latencyMs} error={error} />
    </View>
  );
}
