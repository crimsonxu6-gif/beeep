export interface Size {
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface PreviewTransformContext {
  image: Size;
  preview: Size;
  imageMirrored: boolean;
  previewMirrored: boolean;
}

export type NormalizedBBox = [number, number, number, number];
export type PreviewBBox = [number, number, number, number];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function clampPreviewBBox(bbox: PreviewBBox, preview: Size): PreviewBBox {
  return [
    clamp(bbox[0], 0, preview.width),
    clamp(bbox[1], 0, preview.height),
    clamp(bbox[2], 0, preview.width),
    clamp(bbox[3], 0, preview.height)
  ];
}

export function applyMirrorTransform(point: Point, width: number): Point {
  return { x: width - point.x, y: point.y };
}

export function applyAspectFillCrop(point: Point, image: Size, preview: Size): Point {
  if (image.width <= 0 || image.height <= 0 || preview.width <= 0 || preview.height <= 0) {
    return { x: 0, y: 0 };
  }
  const scale = Math.max(preview.width / image.width, preview.height / image.height);
  const renderedWidth = image.width * scale;
  const renderedHeight = image.height * scale;
  return {
    x: point.x * scale + (preview.width - renderedWidth) / 2,
    y: point.y * scale + (preview.height - renderedHeight) / 2
  };
}

export function previewPointToImagePoint(
  point: Point,
  context: PreviewTransformContext
): Point {
  const { image, preview } = context;
  const scale = Math.max(preview.width / image.width, preview.height / image.height);
  const renderedWidth = image.width * scale;
  const renderedHeight = image.height * scale;
  let imagePoint = {
    x: (point.x - (preview.width - renderedWidth) / 2) / scale,
    y: (point.y - (preview.height - renderedHeight) / 2) / scale
  };
  if (context.imageMirrored !== context.previewMirrored) {
    imagePoint = applyMirrorTransform(imagePoint, image.width);
  }
  return imagePoint;
}

export function modelBBoxToPreviewBBox(
  bbox: NormalizedBBox,
  context: PreviewTransformContext
): PreviewBBox {
  const [x1, y1, x2, y2] = bbox;
  let left = x1 * context.image.width;
  let right = x2 * context.image.width;
  if (context.imageMirrored !== context.previewMirrored) {
    const mirroredLeft = context.image.width - right;
    right = context.image.width - left;
    left = mirroredLeft;
  }
  const topLeft = applyAspectFillCrop(
    { x: left, y: y1 * context.image.height },
    context.image,
    context.preview
  );
  const bottomRight = applyAspectFillCrop(
    { x: right, y: y2 * context.image.height },
    context.image,
    context.preview
  );
  return clampPreviewBBox(
    [topLeft.x, topLeft.y, bottomRight.x, bottomRight.y],
    context.preview
  );
}
