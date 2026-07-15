import { StyleSheet } from "react-native";
import Svg, { Rect } from "react-native-svg";
import { GuidanceOutput } from "@/types/guidance";
import { OverlaySize } from "./GuidanceOverlay";
import { modelBBoxToPreviewBBox } from "@/camera/coordinateTransform";

export function CompositionBoxOverlay({ guidance, size }: { guidance: GuidanceOutput | undefined; size: OverlaySize }) {
  const bbox = guidance?.composition?.bboxNorm;
  if (!bbox || size.width <= 0 || size.height <= 0 || guidance?.composition?.decision === "keep") return null;
  const coordinateContext = guidance.coordinateContext;
  const [x1, y1, x2, y2] = coordinateContext
    ? modelBBoxToPreviewBBox(bbox, {
        image: { width: coordinateContext.imageWidth, height: coordinateContext.imageHeight },
        preview: { width: size.width, height: size.height },
        imageMirrored: coordinateContext.imageMirrored,
        previewMirrored: coordinateContext.previewMirrored
      })
    : [bbox[0] * size.width, bbox[1] * size.height, bbox[2] * size.width, bbox[3] * size.height];
  return (
    <Svg pointerEvents="none" style={StyleSheet.absoluteFill} width={size.width} height={size.height}>
      <Rect
        x={x1}
        y={y1}
        width={x2 - x1}
        height={y2 - y1}
        rx={18}
        stroke="rgba(255,255,255,0.8)"
        strokeWidth={1.5}
        strokeDasharray="10 7"
        fill="transparent"
      />
    </Svg>
  );
}
