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

  if (direction === "hold") {
    return null;
  }

  return (
    <View pointerEvents="none" style={[styles.arrowWrap, positionStyle(direction)]}>
      <Text style={styles.arrow}>{arrows[direction]}</Text>
      <View style={styles.sparkA} />
      <View style={styles.sparkB} />
    </View>
  );
}

const styles = StyleSheet.create({
  arrowWrap: {
    position: "absolute",
    width: 74,
    height: 58,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.86)",
    backgroundColor: "rgba(0,0,0,0.08)",
    transform: [{ rotate: "-6deg" }]
  },
  arrow: {
    color: "#FFFFFF",
    fontSize: 36,
    lineHeight: 42,
    fontWeight: "900"
  },
  sparkA: {
    position: "absolute",
    right: -8,
    top: -7,
    width: 10,
    height: 10,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderColor: "rgba(255,255,255,0.8)",
    transform: [{ rotate: "28deg" }]
  },
  sparkB: {
    position: "absolute",
    left: -9,
    bottom: -4,
    width: 12,
    height: 8,
    borderBottomWidth: 2,
    borderColor: "rgba(255,255,255,0.76)",
    transform: [{ rotate: "-12deg" }]
  },
  center: {
    left: "50%",
    top: "48%",
    marginLeft: -37,
    marginTop: -29
  },
  left: {
    left: 42,
    top: "48%",
    marginTop: -29
  },
  right: {
    right: 42,
    top: "48%",
    marginTop: -29
  },
  up: {
    left: "50%",
    top: 140,
    marginLeft: -37
  },
  down: {
    left: "50%",
    bottom: 272,
    marginLeft: -37
  }
});
