import { StyleSheet, Text, View } from "react-native";

import { StableGuidance } from "@/types/guidance";
import { VisionFeatures } from "@/types/vision";
import { GuidanceDebugState } from "@/ai_engine/guidancePipeline";
import { CompositionMode } from "@/types/guidance";
import { appConfig } from "@/config";

interface GuidanceDebugPanelProps {
  stableGuidance: StableGuidance | null;
  visionFeatures: VisionFeatures | null;
  latencyMs: number | null;
  processing: boolean;
  debugState: GuidanceDebugState;
  compositionMode: CompositionMode;
}

function actionLabel(stableGuidance: StableGuidance | null): string {
  const action = stableGuidance?.guidance.actions[0];
  if (!action) {
    return "none";
  }

  if (action.type === "move_camera" || action.type === "adjust_distance" || action.type === "adjust_angle") {
    return `${action.type} ${action.direction} / ${action.message}`;
  }

  return `${action.type} / ${action.message}`;
}

function visionLabel(visionFeatures: VisionFeatures | null): string {
  if (!visionFeatures) {
    return "waiting";
  }

  const person = visionFeatures.people[0];
  const personText = person ? `person ${Math.round(person.score * 100)}%` : "no person";
  const faceText = `face ${visionFeatures.face.position}/${visionFeatures.face.size}`;
  const sceneText = `${visionFeatures.scene.brightness}/${visionFeatures.scene.clutter}`;

  return `${personText} | ${faceText} | ${sceneText}`;
}

export function GuidanceDebugPanel({
  stableGuidance,
  visionFeatures,
  latencyMs,
  processing,
  debugState,
  compositionMode
}: GuidanceDebugPanelProps) {
  const guidance = stableGuidance?.guidance;

  return (
    <View pointerEvents="none" style={styles.panel}>
      <Text style={styles.line}>Latency: {latencyMs ?? "-"}ms {processing ? "processing" : "idle"}</Text>
      <Text style={styles.line}>Request: {debugState.requestId ?? "-"}</Text>
      <Text style={styles.line}>Frame: {debugState.latestAcceptedFrameId}/{debugState.latestProcessedFrameId}/{debugState.latestRenderedFrameId}</Text>
      <Text style={styles.line}>Stale dropped: {debugState.droppedStaleResultCount}</Text>
      <Text style={styles.line}>Timing P/V/G/T: {guidance?.timing.preflightMs ?? "-"}/{debugState.visionLatencyMs ?? "-"}/{debugState.guidanceLatencyMs ?? "-"}/{debugState.totalLatencyMs ?? "-"}ms</Text>
      <Text style={styles.line}>Mock: {String(appConfig.mockEnabled)} | Mode: {compositionMode}</Text>
      <Text style={styles.line}>Engine: {debugState.guidanceEngine ?? "-"}</Text>
      <Text style={styles.line}>Error: {debugState.errorCode ?? "-"}</Text>
      <Text style={styles.line}>Vision: {visionLabel(visionFeatures)}</Text>
      <Text style={styles.line}>Preflight: {guidance?.subjectPreflight ? `${guidance.subjectPreflight.state}/${String(guidance.subjectPreflight.allowShutterMuse)} ${Math.round(guidance.subjectPreflight.confidence * 100)}%` : "-"}</Text>
      <Text style={styles.line}>Action: {actionLabel(stableGuidance)}</Text>
      <Text style={styles.line}>Priority: {guidance?.priority ?? "-"}</Text>
      <Text style={styles.line}>Problem: {guidance?.problem?.description ?? "-"}</Text>
      <Text style={styles.line}>Reason: {guidance?.reason ?? "-"}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    position: "absolute",
    left: 12,
    right: 12,
    top: 110,
    borderRadius: 8,
    backgroundColor: "rgba(0,0,0,0.58)",
    paddingHorizontal: 10,
    paddingVertical: 8
  },
  line: {
    color: "rgba(255,255,255,0.86)",
    fontSize: 11,
    lineHeight: 15,
    fontWeight: "700"
  }
});
