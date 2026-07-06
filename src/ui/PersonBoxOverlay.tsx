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
          />
        );
      })}
    </>
  );
}

const styles = StyleSheet.create({
  box: {
    position: "absolute",
    borderWidth: 2,
    borderColor: "#40f4c8",
    borderRadius: 4,
    backgroundColor: "rgba(64,244,200,0.05)"
  }
});
