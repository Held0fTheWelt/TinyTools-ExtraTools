export type ComponentBox = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
};

export type DetectedComponent = ComponentBox & {
  id: number;
  pixelCount: number;
};

export type ComponentDetection = {
  width: number;
  height: number;
  labelMap: Int32Array;
  components: DetectedComponent[];
};

export type ComponentDetectionOptions = {
  targetColor?: [number, number, number] | null;
  tolerance?: number;
};

function median(values: number[]): number {
  values.sort((a, b) => a - b);
  return values[Math.floor(values.length / 2)] ?? 255;
}

function estimateBackground(data: Uint8ClampedArray, width: number, height: number): [number, number, number] {
  const rs: number[] = [];
  const gs: number[] = [];
  const bs: number[] = [];
  const step = Math.max(1, Math.floor(Math.max(width, height) / 300));

  const sample = (x: number, y: number) => {
    const i = (y * width + x) * 4;
    rs.push(data[i]);
    gs.push(data[i + 1]);
    bs.push(data[i + 2]);
  };

  for (let x = 0; x < width; x += step) {
    sample(x, 0);
    sample(x, height - 1);
  }
  for (let y = 0; y < height; y += step) {
    sample(0, y);
    sample(width - 1, y);
  }

  return [median(rs), median(gs), median(bs)];
}

function loadImage(dataUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Image could not be loaded."));
    img.src = dataUrl;
  });
}

function findNearestLabel(labelMap: Int32Array, width: number, height: number, x: number, y: number, radius: number): number {
  const ix = Math.round(x);
  const iy = Math.round(y);
  if (ix < 0 || iy < 0 || ix >= width || iy >= height) return 0;
  const direct = labelMap[iy * width + ix];
  if (direct > 0) return direct;

  for (let r = 1; r <= radius; r++) {
    const minX = Math.max(0, ix - r);
    const maxX = Math.min(width - 1, ix + r);
    const minY = Math.max(0, iy - r);
    const maxY = Math.min(height - 1, iy + r);
    for (let px = minX; px <= maxX; px++) {
      const top = labelMap[minY * width + px];
      if (top > 0) return top;
      const bottom = labelMap[maxY * width + px];
      if (bottom > 0) return bottom;
    }
    for (let py = minY + 1; py < maxY; py++) {
      const left = labelMap[py * width + minX];
      if (left > 0) return left;
      const right = labelMap[py * width + maxX];
      if (right > 0) return right;
    }
  }
  return 0;
}

export function componentAt(
  detection: ComponentDetection,
  x: number,
  y: number,
  radius = 7,
): number {
  return findNearestLabel(detection.labelMap, detection.width, detection.height, x, y, radius);
}

export async function detectComponents(
  dataUrl: string,
  options: ComponentDetectionOptions = {},
): Promise<ComponentDetection> {
  const img = await loadImage(dataUrl);
  const width = img.naturalWidth;
  const height = img.naturalHeight;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas nicht verfügbar.");
  ctx.drawImage(img, 0, 0);

  const image = ctx.getImageData(0, 0, width, height);
  const data = image.data;
  const [br, bg, bb] = options.targetColor ?? estimateBackground(data, width, height);
  const tolerance = options.targetColor ? options.tolerance ?? 70 : 35;
  const thresholdSq = tolerance * tolerance;
  const mask = new Uint8Array(width * height);

  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    const dr = data[i] - br;
    const dg = data[i + 1] - bg;
    const db = data[i + 2] - bb;
    const distSq = dr * dr + dg * dg + db * db;
    mask[p] = options.targetColor ? (distSq <= thresholdSq ? 1 : 0) : distSq > thresholdSq ? 1 : 0;
  }

  const labelMap = new Int32Array(width * height);
  const queue = new Int32Array(width * height);
  const minPixels = Math.max(40, Math.floor(width * height * 0.00002));
  const components: DetectedComponent[] = [];
  let nextId = 1;

  for (let start = 0; start < mask.length; start++) {
    if (!mask[start] || labelMap[start]) continue;

    const rawId = -1;
    let head = 0;
    let tail = 0;
    let count = 0;
    let minX = width;
    let minY = height;
    let maxX = 0;
    let maxY = 0;
    queue[tail++] = start;
    labelMap[start] = rawId;

    while (head < tail) {
      const p = queue[head++];
      count++;
      const x = p % width;
      const y = Math.floor(p / width);
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;

      for (let dy = -1; dy <= 1; dy++) {
        const ny = y + dy;
        if (ny < 0 || ny >= height) continue;
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx;
          if (nx < 0 || nx >= width) continue;
          const np = ny * width + nx;
          if (mask[np] && !labelMap[np]) {
            labelMap[np] = rawId;
            queue[tail++] = np;
          }
        }
      }
    }

    const keep = count >= minPixels;
    const id = keep ? nextId++ : 0;
    for (let i = 0; i < tail; i++) labelMap[queue[i]] = id;
    if (keep) components.push({ id, pixelCount: count, minX, minY, maxX, maxY });
  }

  components.sort((a, b) => b.pixelCount - a.pixelCount);
  return { width, height, labelMap, components };
}

export function drawComponentOverlay(
  canvas: HTMLCanvasElement,
  detection: ComponentDetection,
  hoveredId: number | null,
  selectedId: number | null,
): void {
  canvas.width = detection.width;
  canvas.height = detection.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const image = ctx.createImageData(detection.width, detection.height);
  for (let p = 0, i = 0; p < detection.labelMap.length; p++, i += 4) {
    const id = detection.labelMap[p];
    if (!id) continue;
    const selected = selectedId === id;
    const hovered = hoveredId === id;
    if (!selected && !hovered) continue;
    image.data[i] = selected ? 255 : 0;
    image.data[i + 1] = selected ? 145 : 190;
    image.data[i + 2] = selected ? 0 : 255;
    image.data[i + 3] = selected ? 120 : 95;
  }
  ctx.putImageData(image, 0, 0);
}

export async function maskComponentToDataUrl(
  originalDataUrl: string,
  detection: ComponentDetection,
  componentId: number,
): Promise<string> {
  const img = await loadImage(originalDataUrl);
  const source = document.createElement("canvas");
  source.width = detection.width;
  source.height = detection.height;
  const sourceCtx = source.getContext("2d", { willReadFrequently: true });
  if (!sourceCtx) throw new Error("Canvas nicht verfügbar.");
  sourceCtx.drawImage(img, 0, 0);

  const out = sourceCtx.createImageData(detection.width, detection.height);
  for (let p = 0, i = 0; p < detection.labelMap.length; p++, i += 4) {
    if (detection.labelMap[p] === componentId) {
      out.data[i] = 20;
      out.data[i + 1] = 20;
      out.data[i + 2] = 20;
      out.data[i + 3] = 255;
    } else {
      out.data[i] = 255;
      out.data[i + 1] = 255;
      out.data[i + 2] = 255;
      out.data[i + 3] = 255;
    }
  }

  sourceCtx.putImageData(out, 0, 0);
  return source.toDataURL("image/png");
}

export async function maskColorToDataUrl(
  originalDataUrl: string,
  color: [number, number, number],
  tolerance: number,
): Promise<string> {
  const img = await loadImage(originalDataUrl);
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas nicht verfügbar.");
  ctx.drawImage(img, 0, 0);
  const src = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const out = ctx.createImageData(canvas.width, canvas.height);
  const thresholdSq = tolerance * tolerance;

  for (let i = 0; i < src.data.length; i += 4) {
    const dr = src.data[i] - color[0];
    const dg = src.data[i + 1] - color[1];
    const db = src.data[i + 2] - color[2];
    const keep = dr * dr + dg * dg + db * db <= thresholdSq;
    out.data[i] = keep ? 20 : 255;
    out.data[i + 1] = keep ? 20 : 255;
    out.data[i + 2] = keep ? 20 : 255;
    out.data[i + 3] = 255;
  }

  ctx.putImageData(out, 0, 0);
  return canvas.toDataURL("image/png");
}
