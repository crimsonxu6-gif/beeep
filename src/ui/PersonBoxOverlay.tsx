import { StyleSheet, View } from "react-native";

import { PersonDetection, VisionFeatures } from "@/types/vision";
import { OverlaySize } from "./CameraOverlay";

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
            <View style={[styles.corner, styles.topLeft]} />
            <View style={[styles.corner, styles.topRight]} />
            <View style={[styles.corner, styles.bottomLeft]} />
            <View style={[styles.corner, styles.bottomRight]} />
          </View>
        );
      })}
    </>
  );
}

const styles = StyleSheet.create({
  box: {
    position: "absolute",
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.88)",
    borderRadius: 7,
    backgroundColor: "rgba(255,255,255,0.025)",
    transform: [{ rotate: "-0.4deg" }]
  },
  corner: {
    position: "absolute",
    width: 24,
    height: 24,
    borderColor: "rgba(255,255,255,0.96)"
  },
  topLeft: {
    left: -3,
    top: -3,
    borderLeftWidth: 3,
    borderTopWidth: 3
  },
  topRight: {
    right: -3,
    top: -3,
    borderRightWidth: 3,
    borderTopWidth: 3
  },
  bottomLeft: {
    left: -3,
    bottom: -3,
    borderLeftWidth: 3,
    borderBottomWidth: 3
  },
  bottomRight: {
    right: -3,
    bottom: -3,
    borderRightWidth: 3,
    borderBottomWidth: 3
  }
});
