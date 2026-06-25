import type { TrackShape } from "../model/shape";
import { dist, angleDeg, norm, type Vec2 } from "./vec";
import { bezierPoint, bezierDeriv } from "./bezier";

export function segmentMetrics(doc: TrackShape, segId: string) {
  const a = new Map(doc.anchors.map((x) => [x.id, { x: x.x, y: x.y } as Vec2]));
  const s = doc.segments.find((x) => x.id === segId)!;
  const from = a.get(s.from)!;
  const to = a.get(s.to)!;

  if (s.type === "line") {
    return { lengthM: dist(from, to), maxAngleStepDeg: 0, generatedPoints: 2, adaptive: false };
  }

  const adaptive = s.adaptive === true;
  const floor = s.samples ?? 24;
  const n = adaptive ? Math.max(floor, 64) : floor;
  let length = 0;
  let maxAngle = 0;
  let prev = bezierPoint(from, s.handle_from, s.handle_to, to, 0);
  let prevDir = norm(bezierDeriv(from, s.handle_from, s.handle_to, to, 0));

  for (let i = 1; i <= n; i++) {
    const t = i / n;
    const p = bezierPoint(from, s.handle_from, s.handle_to, to, t);
    const dir = norm(bezierDeriv(from, s.handle_from, s.handle_to, to, t));
    length += dist(prev, p);
    maxAngle = Math.max(maxAngle, angleDeg(prevDir, dir));
    prev = p;
    prevDir = dir;
  }

  return { lengthM: length, maxAngleStepDeg: maxAngle, generatedPoints: n + 1, adaptive };
}
