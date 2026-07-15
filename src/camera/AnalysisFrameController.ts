import { CameraView } from "expo-camera";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import { appConfig } from "@/config";
import {
  CameraFacing,
  CapturedFrame,
  DeviceOrientation,
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

    const original = new File(picture.uri);
    const imagePlan = buildAnalysisImagePlan(
      picture.width,
      picture.height,
      appConfig.analysisImageShortEdge,
      appConfig.analysisJpegQuality
    );
    const processed = await manipulateAsync(
      picture.uri,
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
      processedBytes: processedFile.size
    };
    const capture: FrameCaptureMetadata = {
      ...(context.tapTimestamp !== undefined ? { tapTimestamp: context.tapTimestamp } : {}),
      captureStartedAt,
      captureCompletedAt,
      preprocessCompletedAt,
      cameraFacing: context.cameraFacing ?? "back",
      imageMirrored: context.imageMirrored ?? false,
      previewMirrored: context.previewMirrored ?? context.cameraFacing === "front",
      deviceOrientation: context.deviceOrientation ?? "portrait",
      previewWidth: context.previewWidth ?? 0,
      previewHeight: context.previewHeight ?? 0
    };
    return { frameId, timestamp: captureStartedAt, image, capture };
  }
}
