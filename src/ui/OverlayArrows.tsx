import { StyleSheet, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { GuidanceOutput, MoveDirection } from "@/types/guidance";

interface OverlayArrowsProps {
  guidance: GuidanceOutput | null | undefined;
}

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

function rotationStyle(direction: MoveDirection) {
  switch (direction) {
    case "left":
      return { transform: [{ rotate: "180deg" }] };
    case "up":
      return { transform: [{ rotate: "-90deg" }] };
    case "down":
      return { transform: [{ rotate: "90deg" }] };
    case "forward":
      return { transform: [{ rotate: "-38deg" }] };
    case "back":
      return { transform: [{ rotate: "138deg" }] };
    default:
      return undefined;
  }
}

export function OverlayArrows({ guidance }: OverlayArrowsProps) {
  const direction = primaryDirection(guidance);

  if (direction === "hold") {
    return null;
  }

  return (
    <View pointerEvents="none" style={[styles.arrowWrap, positionStyle(direction)]}>
      <Svg width={84} height={58} viewBox="0 0 84 58" style={rotationStyle(direction)}>
        <Path
          d="M 12 34 C 25 20, 45 21, 66 27"
          stroke="rgba(255,255,255,0.94)"
          strokeWidth={3.2}
          strokeLinecap="round"
          fill="none"
        />
        <Path
          d="M 58 17 C 65 20, 70 24, 74 30 C 67 30, 61 32, 55 36"
          stroke="rgba(255,255,255,0.94)"
          strokeWidth={3.2}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <Path
          d="M 18 45 C 28 50, 42 50, 53 45"
          stroke="rgba(255,255,255,0.38)"
          strokeWidth={1.8}
          strokeLinecap="round"
          fill="none"
        />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  arrowWrap: {
    position: "absolute",
    width: 86,
    height: 60,
    alignItems: "center",
    justifyContent: "center"
  },
  center: {
    left: "50%",
    top: "48%",
    marginLeft: -43,
    marginTop: -30
  },
  left: {
    left: 34,
    top: "48%",
    marginTop: -30
  },
  right: {
    right: 34,
    top: "48%",
    marginTop: -30
  },
  up: {
    left: "50%",
    top: 140,
    marginLeft: -43
  },
  down: {
    left: "50%",
    bottom: 274,
    marginLeft: -43
  }
});
