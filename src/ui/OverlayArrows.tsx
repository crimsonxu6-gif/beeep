import { StyleSheet, View } from "react-native";
import Svg, { Circle, Path } from "react-native-svg";

import { GuidanceAction, GuidanceOutput, MoveDirection } from "@/types/guidance";
import { GuidanceVisualVariant } from "./guidanceVisuals";

interface OverlayArrowsProps {
  guidance: GuidanceOutput | null | undefined;
  variant: GuidanceVisualVariant;
}

function primaryDirection(guidance: GuidanceOutput | null | undefined): MoveDirection {
  const action = guidance?.actions[0];
  if (!action) {
    return "hold";
  }

  if (action.type === "move_camera") {
    return action.direction;
  }

  if (action.type === "adjust_distance") {
    return action.direction === "closer" ? "forward" : "back";
  }

  if (action.type === "adjust_angle") {
    if (action.direction === "lower") {
      return "down";
    }
    if (action.direction === "raise") {
      return "up";
    }
  }

  return "hold";
}

function shouldShowArrow(action: GuidanceAction | undefined): boolean {
  return Boolean(action && ["move_camera", "adjust_distance", "adjust_angle"].includes(action.type));
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

function ArrowDecoration({ variant }: { variant: GuidanceVisualVariant }) {
  switch (variant) {
    case "loop":
      return (
        <Circle
          cx={42}
          cy={30}
          r={27}
          stroke="rgba(255,255,255,0.36)"
          strokeWidth={1.6}
          strokeLinecap="round"
          strokeDasharray="5 8"
          fill="rgba(0,0,0,0.08)"
        />
      );
    case "cloud":
      return (
        <Path
          d="M 16 39 C 10 31, 15 21, 25 22 C 31 12, 46 13, 51 23 C 63 20, 73 27, 70 38 C 59 45, 29 47, 16 39"
          stroke="rgba(255,255,255,0.34)"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="rgba(0,0,0,0.1)"
        />
      );
    case "dashed":
      return (
        <Path
          d="M 12 45 C 27 54, 57 53, 72 43"
          stroke="rgba(255,255,255,0.36)"
          strokeWidth={1.6}
          strokeLinecap="round"
          strokeDasharray="4 7"
          fill="none"
        />
      );
    case "underline":
      return (
        <Path
          d="M 18 48 C 32 52, 52 52, 68 47"
          stroke="rgba(255,255,255,0.42)"
          strokeWidth={1.8}
          strokeLinecap="round"
          fill="none"
        />
      );
    case "note":
      return (
        <Path
          d="M 18 15 C 30 10, 55 10, 67 18 M 18 45 C 32 50, 54 49, 68 43"
          stroke="rgba(255,255,255,0.32)"
          strokeWidth={1.5}
          strokeLinecap="round"
          fill="none"
        />
      );
    default:
      return (
        <Path
          d="M 18 45 C 28 50, 42 50, 53 45"
          stroke="rgba(255,255,255,0.34)"
          strokeWidth={1.6}
          strokeLinecap="round"
          fill="none"
        />
      );
  }
}

export function OverlayArrows({ guidance, variant }: OverlayArrowsProps) {
  const action = guidance?.actions[0];
  if (!shouldShowArrow(action)) {
    return null;
  }

  const direction = primaryDirection(guidance);

  if (direction === "hold") {
    return null;
  }

  const dashedProps = variant === "dashed" ? { strokeDasharray: [7, 7] as const } : {};

  return (
    <View pointerEvents="none" style={[styles.arrowWrap, positionStyle(direction)]}>
      <Svg width={84} height={58} viewBox="0 0 84 58" style={rotationStyle(direction)}>
        <ArrowDecoration variant={variant} />
        <Path
          d="M 12 34 C 25 20, 45 21, 66 27"
          stroke="rgba(255,255,255,0.9)"
          strokeWidth={2.8}
          strokeLinecap="round"
          fill="none"
          {...dashedProps}
        />
        <Path
          d="M 58 17 C 65 20, 70 24, 74 30 C 67 30, 61 32, 55 36"
          stroke="rgba(255,255,255,0.9)"
          strokeWidth={2.8}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          {...dashedProps}
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
