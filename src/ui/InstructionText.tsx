import { StyleSheet, Text, View } from "react-native";

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
      <View style={styles.bubble}>
        <Text numberOfLines={1} adjustsFontSizeToFit style={styles.instruction}>
          {error ? "保持当前" : text}
        </Text>
        {statusText ? <Text style={styles.status}>{statusText}</Text> : null}
      </View>
      <View style={styles.tail} />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 34,
    right: 34,
    bottom: 190,
    alignItems: "center",
    transform: [{ rotate: "-1deg" }]
  },
  bubble: {
    minHeight: 64,
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    borderWidth: 2,
    borderStyle: "dashed",
    borderColor: "rgba(255,255,255,0.92)",
    backgroundColor: "rgba(0,0,0,0.22)",
    paddingHorizontal: 18,
    paddingVertical: 9
  },
  tail: {
    width: 28,
    height: 14,
    marginTop: -2,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderColor: "rgba(255,255,255,0.9)",
    transform: [{ rotate: "-8deg" }]
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
    marginTop: 2,
    color: "rgba(255,255,255,0.72)",
    fontSize: 11,
    fontWeight: "700"
  }
});
