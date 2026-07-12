import { StyleSheet, Text, View } from "react-native";

import { ModelStatus } from "@/types/guidance";

export function ModelStatusMessage({
  status,
  hasGuidance
}: {
  status: ModelStatus;
  hasGuidance: boolean;
}) {
  const waiting = status.severity === "waiting";
  return (
    <View
      pointerEvents="none"
      style={[styles.wrap, hasGuidance && styles.withGuidance, waiting ? styles.waiting : styles.error]}
    >
      <Text style={styles.message}>{status.message}</Text>
      <Text style={styles.suggestion}>{status.suggestion}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: 44,
    right: 44,
    bottom: 190,
    minHeight: 68,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 18,
    paddingVertical: 10
  },
  waiting: {
    borderColor: "rgba(255,255,255,0.28)",
    backgroundColor: "rgba(16,16,18,0.62)"
  },
  error: {
    borderColor: "rgba(255,255,255,0.38)",
    backgroundColor: "rgba(20,20,22,0.76)"
  },
  withGuidance: {
    bottom: 282
  },
  message: {
    color: "#FFFFFF",
    textAlign: "center",
    fontSize: 17,
    lineHeight: 23,
    fontWeight: "800"
  },
  suggestion: {
    marginTop: 3,
    color: "rgba(255,255,255,0.68)",
    textAlign: "center",
    fontSize: 13,
    lineHeight: 18,
    fontWeight: "600"
  }
});
