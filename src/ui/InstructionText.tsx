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
      <Text numberOfLines={1} adjustsFontSizeToFit style={styles.instruction}>
        {error ? "保持当前" : text}
      </Text>
      {statusText ? <Text style={styles.status}>{statusText}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 24,
    right: 24,
    bottom: 46,
    minHeight: 58,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.24)",
    backgroundColor: "rgba(0,0,0,0.42)",
    paddingHorizontal: 18,
    paddingVertical: 10
  },
  instruction: {
    width: "100%",
    color: "#ffffff",
    textAlign: "center",
    fontSize: 24,
    fontWeight: "800"
  },
  status: {
    marginTop: 3,
    color: "rgba(255,255,255,0.64)",
    fontSize: 11,
    fontWeight: "600"
  }
});
