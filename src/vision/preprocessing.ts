import { CapturedFrame } from "@/types/frame";
import { VisionFeatures } from "@/types/vision";
import { buildMockVisionFeatures } from "./featureBuilder";

export interface VisionPreprocessor {
  preprocess(frame: CapturedFrame): Promise<VisionFeatures>;
}

export class PrototypeVisionPreprocessor implements VisionPreprocessor {
  async preprocess(frame: CapturedFrame): Promise<VisionFeatures> {
    return buildMockVisionFeatures(frame);
  }
}
