import { StyleSheet, Text, View } from "react-native";

import { GuidanceOutput, MoveDirection } from "@/types/guidance";

interface OverlayArrowsProps {
  guidance: GuidanceOutput | null | undefined;
}

const arrows: Record<MoveDirection, string> = {
  left: "←",
  right: "→",
  up: "↑",
  down: "↓",
  forward: "↗",
  back: "↙",
  hold: "✓"
};

function primaryDirection(guidance: GuidanceOutput | null | undefined): MoveDirection {
  const moveAction = guidance?.actions.find((action) => action.type === "move_camera");
  if (moveAction?.type === "move_camera") {
    return moveAction.direction;
  }

  const framingAction = guidance?.actions.find((action) => action.type === "framing_hint");
  if (framingAction?.type === "framing_hint" && framingAction.direction) {
    return framingAction.direction;
  }

  return "hold";
}

function positionStyle(direction: MoveDirection) {
  switch (direction) {
    case "left":
      return styles.left;
    case "right":
      return styles.right;
    case "up":
      return styles.up;
    case "down":
      return styles.down;
    default:
      return styles.center;
  }
}

export function OverlayArrows({ guidance }: OverlayArrowsProps) {
  const direction = primaryDirection(guidance);

  return (
    <View pointerEvents="none" style={[styles.arrowWrap, positionStyle(direction)]}>
      <Text style={styles.arrow}>{arrows[direction]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  arrowWrap: {
    position: "absolute",
    width: 72,
    height: 72,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 36,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.34)",
    backgroundColor: "rgba(0,0,0,0.24)"
  },
  arrow: {
    color: "#ffffff",
    fontSize: 42,
    lineHeight: 52,
    fontWeight: "800"
  },
  center: {
    left: "50%",
    top: "48%",
    transform: [{ translateX: -36 }, { translateY: -36 }]
  },
  left: {
    left: 28,
    top: "48%",
    transform: [{ translateY: -36 }]
  },
  right: {
    right: 28,
    top: "48%",
    transform: [{ translateY: -36 }]
  },
  up: {
    left: "50%",
    top: 86,
    transform: [{ translateX: -36 }]
  },
  down: {
    left: "50%",
    bottom: 142,
    transform: [{ translateX: -36 }]
  }
});
