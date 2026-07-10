import { StyleSheet } from "react-native";
import Svg, { Rect } from "react-native-svg";
import { GuidanceOutput } from "@/types/guidance";
import { OverlaySize } from "./GuidanceOverlay";

export function CompositionBoxOverlay({ guidance, size }: { guidance: GuidanceOutput | undefined; size: OverlaySize }) {
  const bbox = guidance?.composition?.bboxNorm;
  if (!bbox || size.width <= 0 || size.height <= 0 || guidance?.composition?.decision === "keep") return null;
  const [x1, y1, x2, y2] = bbox;
  return (
    <Svg pointerEvents="none" style={StyleSheet.absoluteFill} width={size.width} height={size.height}>
      <Rect
        x={x1 * size.width}
        y={y1 * size.height}
        width={(x2 - x1) * size.width}
        height={(y2 - y1) * size.height}
        rx={18}
        stroke="rgba(255,255,255,0.8)"
        strokeWidth={1.5}
        strokeDasharray="10 7"
        fill="transparent"
      />
    </Svg>
  );
}
