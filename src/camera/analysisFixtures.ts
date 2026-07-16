import { Asset } from "expo-asset";
import frontPortrait from "../../assets/analysis-fixtures/front-portrait.jpg";
import fullBodyDistant from "../../assets/analysis-fixtures/full-body-distant.jpg";
import sideProfile from "../../assets/analysis-fixtures/side-profile.jpg";
import backView from "../../assets/analysis-fixtures/back-view.jpg";
import groupEdge from "../../assets/analysis-fixtures/group-edge.jpg";
import lookingDown from "../../assets/analysis-fixtures/looking-down.jpg";
import landscapeGroup from "../../assets/analysis-fixtures/landscape-group.jpg";
import largePortrait from "../../assets/analysis-fixtures/large-portrait.jpg";

import { AnalysisSourceFrame, CameraFacing, DeviceOrientation } from "@/types/frame";

export interface AnalysisFixture {
  id: string;
  label: string;
  module: number;
  cameraFacing: CameraFacing;
  mirrored: boolean;
  orientation: DeviceOrientation;
  width: number;
  height: number;
  bytes: number;
}

export const ANALYSIS_FIXTURES: readonly AnalysisFixture[] = [
  { id: "front_portrait", label: "正面半身", module: frontPortrait, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 156696 },
  { id: "full_body", label: "远距离全身", module: fullBodyDistant, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 190234 },
  { id: "side_profile", label: "侧脸", module: sideProfile, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 167607 },
  { id: "back_view", label: "背影", module: backView, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 364802 },
  { id: "group_edge", label: "多人边缘", module: groupEdge, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 196838 },
  { id: "looking_down", label: "低头人物", module: lookingDown, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 960, height: 1280, bytes: 124606 },
  { id: "landscape_group", label: "横图多人", module: landscapeGroup, cameraFacing: "back", mirrored: false, orientation: "landscape_right", width: 1280, height: 960, bytes: 284595 },
  { id: "large_portrait", label: "高分辨率人像", module: largePortrait, cameraFacing: "back", mirrored: false, orientation: "portrait", width: 3024, height: 4032, bytes: 1174344 }
] as const;

export async function bundledFixtureSource(
  fixture: AnalysisFixture,
  overrides: Partial<Pick<AnalysisSourceFrame, "cameraFacing" | "imageMirrored" | "previewMirrored" | "deviceOrientation">> = {}
): Promise<AnalysisSourceFrame> {
  const captureStartedAt = Date.now();
  const asset = Asset.fromModule(fixture.module);
  await asset.downloadAsync();
  const uri = asset.localUri ?? asset.uri;
  if (!uri || !asset.width || !asset.height) {
    throw new Error(`Fixture ${fixture.id} could not be resolved`);
  }
  return {
    uri,
    width: asset.width,
    height: asset.height,
    cameraFacing: overrides.cameraFacing ?? fixture.cameraFacing,
    imageMirrored: overrides.imageMirrored ?? fixture.mirrored,
    previewMirrored: overrides.previewMirrored ?? fixture.mirrored,
    deviceOrientation: overrides.deviceOrientation ?? fixture.orientation,
    source: "fixture",
    captureStartedAt,
    captureCompletedAt: Date.now()
  };
}

export function galleryFixtureSource(asset: {
  uri: string;
  width: number;
  height: number;
}, options: Pick<AnalysisSourceFrame, "cameraFacing" | "imageMirrored" | "previewMirrored" | "deviceOrientation">): AnalysisSourceFrame {
  const timestamp = Date.now();
  return {
    ...asset,
    ...options,
    source: "gallery",
    captureStartedAt: timestamp,
    captureCompletedAt: timestamp
  };
}
