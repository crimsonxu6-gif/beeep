import { StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

interface InstructionTextProps {
  text: string;
  processing: boolean;
  latencyMs: number | null;
  error: string | null;
}

export function InstructionText({ text, processing, latencyMs, error }: InstructionTextProps) {
  const statusText = error ? "连接异常" : processing ? "分析中" : latencyMs ? `${latencyMs}ms` : "";

  return (
    <View pointerEvents="none" style={styles.wrap}>
      <Svg pointerEvents="none" style={styles.outline} viewBox="0 0 300 84" preserveAspectRatio="none">
        <Path
          d="M 24 10 C 84 2, 218 4, 278 14 C 294 30, 290 62, 270 72 C 200 80, 88 78, 22 70 C 4 52, 7 25, 24 10"
          stroke="rgba(255,255,255,0.9)"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="rgba(0,0,0,0.24)"
        />
        <Path
          d="M 106 72 C 118 82, 134 83, 148 72"
          stroke="rgba(255,255,255,0.74)"
          strokeWidth={2}
          strokeLinecap="round"
          fill="none"
        />
      </Svg>
      <View style={styles.content}>
        <Text numberOfLines={1} adjustsFontSizeToFit style={styles.instruction}>
          {error ? "保持当前" : text}
        </Text>
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
    minHeight: 84,
    transform: [{ rotate: "-1deg" }]
  },
  outline: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0
  },
  content: {
    minHeight: 78,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 28,
    paddingVertical: 10
  },
  instruction: {
    width: "100%",
    color: "#FFFFFF",
    textAlign: "center",
    fontSize: 25,
    lineHeight: 31,
    fontWeight: "800"
  },
  status: {
    marginTop: 1,
    color: "rgba(255,255,255,0.7)",
    fontSize: 11,
    fontWeight: "700"
  }
});
