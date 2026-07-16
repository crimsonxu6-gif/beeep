import { CameraView } from "expo-camera";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import { appConfig } from "@/config";
import {
  CameraFacing,
  AnalysisSourceFrame,
  CapturedFrame,
  DeviceOrientation,
  AnalysisApiMode,
  AnalysisUploadMode,
  SimulatedNetworkProfile,
  AnalysisFailureScenario,
  FrameCaptureMetadata,
  FrameImage
} from "@/types/frame";
import { ANALYSIS_CAPTURE_OPTIONS, buildAnalysisImagePlan } from "./analysisImagePlan";

export interface AnalysisCaptureContext {
  tapTimestamp?: number;
  cameraFacing?: CameraFacing;
  imageMirrored?: boolean;
  previewMirrored?: boolean;
  deviceOrientation?: DeviceOrientation;
  previewWidth?: number;
  previewHeight?: number;
  apiMode?: AnalysisApiMode;
  uploadMode?: AnalysisUploadMode;
  networkProfile?: SimulatedNetworkProfile;
  failureScenario?: AnalysisFailureScenario;
}

export class AnalysisFrameController {
  async captureAnalysisFrame(
    camera: CameraView,
    frameId: number,
    context: AnalysisCaptureContext = {}
  ): Promise<CapturedFrame | null> {
    const captureStartedAt = Date.now();
    const picture = await camera.takePictureAsync(ANALYSIS_CAPTURE_OPTIONS);
    if (!picture) return null;
    const captureCompletedAt = Date.now();

    return this.processAnalysisSourceFrame({
      uri: picture.uri,
      width: picture.width,
      height: picture.height,
      cameraFacing: context.cameraFacing ?? "back",
      imageMirrored: context.imageMirrored ?? false,
      previewMirrored: context.previewMirrored ?? context.cameraFacing === "front",
      deviceOrientation: context.deviceOrientation ?? "portrait",
      source: "camera",
      captureStartedAt,
      captureCompletedAt
    }, frameId, context);
  }

  async processAnalysisSourceFrame(
    source: AnalysisSourceFrame,
    frameId: number,
    context: AnalysisCaptureContext = {}
  ): Promise<CapturedFrame> {
    const captureStartedAt = source.captureStartedAt ?? Date.now();
    const captureCompletedAt = source.captureCompletedAt ?? Date.now();
    const original = new File(source.uri);
    const imagePlan = buildAnalysisImagePlan(
      source.width,
      source.height,
      appConfig.analysisImageShortEdge,
      appConfig.analysisJpegQuality
    );
    const processed = await manipulateAsync(
      source.uri,
      [{ resize: imagePlan.resize }],
      {
        base64: false,
        compress: imagePlan.jpegQuality,
        format: SaveFormat.JPEG
      }
    );
    const processedFile = new File(processed.uri);
    const preprocessCompletedAt = Date.now();
    const image: FrameImage = {
      uri: processed.uri,
      width: processed.width,
      height: processed.height,
      mimeType: "image/jpeg",
      originalBytes: original.size,
      processedImageBytes: processedFile.size,
      originalWidth: source.width,
      originalHeight: source.height
    };
    const capture: FrameCaptureMetadata = {
      source: source.source,
      ...(context.tapTimestamp !== undefined ? { tapTimestamp: context.tapTimestamp } : {}),
      captureStartedAt,
      captureCompletedAt,
      preprocessCompletedAt,
      cameraFacing: context.cameraFacing ?? source.cameraFacing,
      imageMirrored: context.imageMirrored ?? source.imageMirrored,
      previewMirrored: context.previewMirrored ?? source.previewMirrored,
      deviceOrientation: context.deviceOrientation ?? source.deviceOrientation,
      previewWidth: context.previewWidth ?? 0,
      previewHeight: context.previewHeight ?? 0,
      ...(context.apiMode ? { apiMode: context.apiMode } : {}),
      ...(context.uploadMode ? { uploadMode: context.uploadMode } : {}),
      ...(context.networkProfile ? { networkProfile: context.networkProfile } : {}),
      ...(context.failureScenario ? { failureScenario: context.failureScenario } : {})
    };
    return { frameId, timestamp: captureStartedAt, image, capture };
  }
}
