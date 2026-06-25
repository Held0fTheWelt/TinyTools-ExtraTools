import type { TrackShape } from "../model/shape";

export type ReferenceImageLayer = {
  href: string;
  name: string;
  widthPx: number;
  heightPx: number;
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
  visible: boolean;
};

type ImportMetadata = {
  image_size_px?: unknown;
  image_transform?: {
    world_rect?: {
      x?: unknown;
      y?: unknown;
      width?: unknown;
      height?: unknown;
    };
  };
};

function finiteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

export function referenceImageFromShape(
  shape: TrackShape,
  href: string,
  name: string,
): ReferenceImageLayer | null {
  const metadata = shape.metadata as { import?: ImportMetadata } | undefined;
  const importMeta = metadata?.import;
  const imageSize = importMeta?.image_size_px;
  const rect = importMeta?.image_transform?.world_rect;

  if (!Array.isArray(imageSize) || imageSize.length < 2 || !rect) return null;
  const [widthPx, heightPx] = imageSize;
  if (
    !finiteNumber(widthPx) ||
    !finiteNumber(heightPx) ||
    !finiteNumber(rect.x) ||
    !finiteNumber(rect.y) ||
    !finiteNumber(rect.width) ||
    !finiteNumber(rect.height) ||
    rect.width <= 0 ||
    rect.height <= 0
  ) {
    return null;
  }

  return {
    href,
    name,
    widthPx,
    heightPx,
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
    opacity: 0.5,
    visible: true,
  };
}
