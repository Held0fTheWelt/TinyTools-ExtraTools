import type { Vec2 } from "../geometry/vec";
import { dist, lerp } from "../geometry/vec";

export const meshPieceEstimate = (lengthM: number, pieceLengthM: number): number =>
  Math.ceil(lengthM / pieceLengthM);

export function meshBoundaries(pts: Vec2[], pieceLengthM: number): Vec2[] {
  const out: Vec2[] = [];
  let acc = 0;
  let nextAt = pieceLengthM;

  for (let i = 1; i < pts.length; i++) {
    const segLen = dist(pts[i - 1], pts[i]);
    while (nextAt < acc + segLen) {
      const t = (nextAt - acc) / segLen;
      out.push(lerp(pts[i - 1], pts[i], t));
      nextAt += pieceLengthM;
    }
    acc += segLen;
  }

  return out;
}
