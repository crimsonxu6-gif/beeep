import { StyleSheet } from "react-native";
import Svg, { Circle, Line } from "react-native-svg";
import { GuidanceOutput } from "@/types/guidance";
import { OverlaySize } from "./GuidanceOverlay";

const BONES = [
  ["left_shoulder", "right_shoulder"], ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"], ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"], ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"], ["left_hip", "right_hip"],
  ["left_hip", "left_knee"], ["right_hip", "right_knee"],
  ["left_knee", "left_ankle"], ["right_knee", "right_ankle"]
] as const;

export function PoseSkeletonOverlay({ guidance, size }: { guidance: GuidanceOutput | undefined; size: OverlaySize }) {
  const keypoints = guidance?.pose?.keypoints;
  if (!keypoints || size.width <= 0 || size.height <= 0) return null;
  const points = new Map(keypoints.map((point) => [point.name, point]));
  return (
    <Svg pointerEvents="none" style={StyleSheet.absoluteFill} width={size.width} height={size.height}>
      {BONES.map(([from, to]) => {
        const a = points.get(from); const b = points.get(to);
        if (!a || !b || a.visibility < 0.4 || b.visibility < 0.4) return null;
        return <Line key={`${from}-${to}`} x1={a.x * size.width} y1={a.y * size.height} x2={b.x * size.width} y2={b.y * size.height} stroke="rgba(255,255,255,0.62)" strokeWidth={2} />;
      })}
      {keypoints.filter((point) => point.visibility >= 0.4).map((point) => (
        <Circle key={point.name} cx={point.x * size.width} cy={point.y * size.height} r={3} fill="rgba(255,255,255,0.84)" />
      ))}
    </Svg>
  );
}
