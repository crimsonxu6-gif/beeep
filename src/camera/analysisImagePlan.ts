export interface AnalysisImagePlan {
  resize: { width?: number; height?: number };
  jpegQuality: number;
}

export const ANALYSIS_CAPTURE_OPTIONS = {
  base64: false,
  quality: 0.8,
  skipProcessing: false,
  shutterSound: false
} as const;

export function buildAnalysisImagePlan(
  width: number,
  height: number,
  shortEdge: number,
  jpegQuality: number
): AnalysisImagePlan {
  if (width <= 0 || height <= 0 || shortEdge <= 0) {
    throw new Error("Image dimensions and short edge must be positive");
  }
  const resize = width <= height
    ? { width: Math.min(shortEdge, width) }
    : { height: Math.min(shortEdge, height) };
  return { resize, jpegQuality };
}
