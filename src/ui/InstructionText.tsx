import { StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { GuidanceVisualVariant } from "./guidanceVisuals";

interface InstructionTextProps {
  primary: string;
  secondary: string | null;
  latencyMs: number | null;
  variant: GuidanceVisualVariant;
}

function InstructionFrame({ variant }: { variant: GuidanceVisualVariant }) {
  const dashedProps = variant === "dashed" ? { strokeDasharray: [8, 8] as const } : {};

  if (variant === "underline") {
    return (
      <Svg pointerEvents="none" style={styles.outline} viewBox="0 0 300 84" preserveAspectRatio="none">
        <Path
          d="M 72 61 C 118 67, 182 67, 230 60"
          stroke="rgba(255,255,255,0.82)"
          strokeWidth={2.4}
          strokeLinecap="round"
          fill="none"
        />
        <Path
          d="M 84 18 C 126 10, 176 11, 214 19"
          stroke="rgba(255,255,255,0.28)"
          strokeWidth={1.4}
          strokeLinecap="round"
          fill="none"
        />
      </Svg>
    );
  }

  if (variant === "loop") {
    return (
      <Svg pointerEvents="none" style={styles.outline} viewBox="0 0 300 84" preserveAspectRatio="none">
        <Path
          d="M 31 18 C 92 3, 211 6, 270 22 C 286 36, 282 59, 261 69 C 190 80, 89 78, 28 66 C 5 48, 10 26, 31 18"
          stroke="rgba(255,255,255,0.84)"
          strokeWidth={2.1}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="rgba(0,0,0,0.18)"
        />
      </Svg>
    );
  }

  if (variant === "note") {
    return (
      <Svg pointerEvents="none" style={styles.outline} viewBox="0 0 300 84" preserveAspectRatio="none">
        <Path
          d="M 28 14 C 95 8, 208 10, 273 15 C 281 32, 279 53, 267 68 C 204 75, 91 75, 27 68 C 16 51, 17 30, 28 14"
          stroke="rgba(255,255,255,0.82)"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="rgba(0,0,0,0.2)"
        />
        <Path
          d="M 39 71 C 64 77, 89 77, 112 70"
          stroke="rgba(255,255,255,0.28)"
          strokeWidth={1.4}
          strokeLinecap="round"
          fill="none"
        />
      </Svg>
    );
  }

  return (
    <Svg pointerEvents="none" style={styles.outline} viewBox="0 0 300 84" preserveAspectRatio="none">
      <Path
        d="M 24 10 C 84 2, 218 4, 278 14 C 294 30, 290 62, 270 72 C 200 80, 88 78, 22 70 C 4 52, 7 25, 24 10"
        stroke="rgba(255,255,255,0.82)"
        strokeWidth={2.1}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="rgba(0,0,0,0.2)"
        {...dashedProps}
      />
      <Path
        d="M 106 72 C 118 82, 134 83, 148 72"
        stroke="rgba(255,255,255,0.58)"
        strokeWidth={1.8}
        strokeLinecap="round"
        fill="none"
      />
    </Svg>
  );
}

export function InstructionText({ primary, secondary, latencyMs, variant }: InstructionTextProps) {
  const statusText = latencyMs ? `${latencyMs}ms` : "";

  return (
    <View pointerEvents="none" style={styles.wrap}>
      <InstructionFrame variant={variant} />
      <View style={styles.content}>
        <Text numberOfLines={1} adjustsFontSizeToFit style={styles.instruction}>
          {primary}
        </Text>
        {secondary ? (
          <Text numberOfLines={1} adjustsFontSizeToFit style={styles.secondary}>
            {secondary}
          </Text>
        ) : null}
        {statusText ? <Text style={styles.status}>{statusText}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 34,
    right: 34,
    bottom: 190,
    minHeight: 96,
    transform: [{ rotate: "-0.5deg" }]
  },
  outline: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0
  },
  content: {
    minHeight: 92,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 28,
    paddingVertical: 10
  },
  instruction: {
    width: "100%",
    color: "#FFFFFF",
    textAlign: "center",
    fontSize: 24,
    lineHeight: 30,
    fontWeight: "800"
  },
  secondary: {
    width: "100%",
    marginTop: 2,
    color: "rgba(255,255,255,0.72)",
    textAlign: "center",
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "700"
  },
  status: {
    marginTop: 1,
    color: "rgba(255,255,255,0.62)",
    fontSize: 11,
    fontWeight: "700"
  }
});
