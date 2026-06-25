export interface View {
  vbMinX: number;
  vbMinY: number;
  vbW: number;
  vbH: number;
  pxW: number;
  pxH: number;
  flipY: boolean;
}

export function screenToWorld(px: number, py: number, v: View): { x: number; y: number } {
  const x = v.vbMinX + (px / v.pxW) * v.vbW;
  const yTop = v.vbMinY + (py / v.pxH) * v.vbH;
  return { x, y: v.flipY ? v.vbMinY + v.vbH - (yTop - v.vbMinY) : yTop };
}
