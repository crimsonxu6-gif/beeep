import { StyleSheet, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import type { OverlaySize } from "@/components/GuidanceOverlay";
import { PersonDetection, VisionFeatures } from "@/types/vision";

interface PersonBoxOverlayProps {
  visionFeatures: VisionFeatures | null;
  overlaySize: OverlaySize;
}

function mapBoxToOverlay(
  person: PersonDetection,
  features: VisionFeatures,
  overlaySize: OverlaySize
) {
  const { width: imageWidth, height: imageHeight } = features.imageSize;
  const { width: viewWidth, height: viewHeight } = overlaySize;
  if (!imageWidth || !imageHeight || !viewWidth || !viewHeight) {
    return null;
  }

  const scale = Math.max(viewWidth / imageWidth, viewHeight / imageHeight);
  const renderedWidth = imageWidth * scale;
  const renderedHeight = imageHeight * scale;
  const offsetX = (viewWidth - renderedWidth) / 2;
  const offsetY = (viewHeight - renderedHeight) / 2;
  const [x, y, width, height] = person.bbox;

  return {
    left: offsetX + x * scale,
    top: offsetY + y * scale,
    width: width * scale,
    height: height * scale
  };
}

function DoodleSubjectFrame({ width, height }: { width: number; height: number }) {
  const w = Math.max(24, width);
  const h = Math.max(24, height);

  const outerPath = [
    `M 18 12`,
    `C ${w * 0.28} 2, ${w * 0.68} 8, ${w - 18} 14`,
    `C ${w + 2} ${h * 0.32}, ${w - 8} ${h * 0.72}, ${w - 20} ${h - 18}`,
    `C ${w * 0.68} ${h + 2}, ${w * 0.28} ${h - 2}, 16 ${h - 14}`,
    `C -2 ${h * 0.68}, 7 ${h * 0.3}, 18 12`
  ].join(" ");

  const innerPath = [
    `M 28 24`,
    `C ${w * 0.34} 18, ${w * 0.62} 20, ${w - 30} 28`,
    `C ${w - 18} ${h * 0.42}, ${w - 22} ${h * 0.66}, ${w - 34} ${h - 30}`,
    `C ${w * 0.62} ${h - 20}, ${w * 0.36} ${h - 18}, 30 ${h - 28}`
  ].join(" ");

  return (
    <Svg pointerEvents="none" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <Path
        d={outerPath}
        stroke="rgba(255,255,255,0.9)"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="12 8"
        fill="rgba(255,255,255,0.018)"
      />
      <Path
        d={innerPath}
        stroke="rgba(255,255,255,0.42)"
        strokeWidth={1.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </Svg>
  );
}

export function PersonBoxOverlay({ visionFeatures, overlaySize }: PersonBoxOverlayProps) {
  if (!visionFeatures) {
    return null;
  }

  return (
    <>
      {visionFeatures.people.map((person) => {
        const box = mapBoxToOverlay(person, visionFeatures, overlaySize);
        if (!box) {
          return null;
        }

        return (
          <View
            key={person.id}
            pointerEvents="none"
            style={[
              styles.box,
              {
                left: box.left,
                top: box.top,
                width: box.width,
                height: box.height
              }
            ]}
          >
            <DoodleSubjectFrame width={box.width} height={box.height} />
          </View>
        );
      })}
    </>
  );
}

const styles = StyleSheet.create({
  box: {
    position: "absolute",
    transform: [{ rotate: "-0.4deg" }]
  }
});
