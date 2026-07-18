import { StyleSheet } from "react-native";
import Svg, { Rect } from "react-native-svg";
import { GuidanceOutput } from "@/types/guidance";
import { OverlaySize } from "./GuidanceOverlay";
import { modelBBoxToPreviewBBox } from "@/camera/coordinateTransform";

const loggedBBoxEvidence = new Set<string>();

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
  if (typeof __DEV__ !== "undefined" && __DEV__) {
    const evidenceKey = `${guidance.requestId}:${size.width}x${size.height}`;
    if (!loggedBBoxEvidence.has(evidenceKey)) {
      loggedBBoxEvidence.add(evidenceKey);
      console.info("BEEEP_BBOX_OVERLAY", JSON.stringify({
        requestId: guidance.requestId,
        frameId: guidance.frameId,
        previewWidth: size.width,
        previewHeight: size.height,
        cameraFacing: coordinateContext?.cameraFacing ?? "unknown",
        imageMirrored: coordinateContext?.imageMirrored ?? false,
        previewMirrored: coordinateContext?.previewMirrored ?? false,
        deviceOrientation: coordinateContext?.deviceOrientation ?? "unknown",
        bboxNorm: bbox,
        transformedBboxPx: [x1, y1, x2, y2],
        inBounds: x1 >= 0 && y1 >= 0 && x2 <= size.width && y2 <= size.height
      }));
    }
  }
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
