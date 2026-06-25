import type { Vec2 } from "./vec";
import { dist } from "./vec";
import { bezierPoint } from "./bezier";
import type { TrackShape } from "../model/shape";

const TOL = { chord: 0.35, angle: 5.0, maxLen: 30.0, minLen: 0.5, maxDepth: 24 };

function hullFlatness(p0: Vec2, p1: Vec2, p2: Vec2, p3: Vec2): number {
  const dx = p3.x - p0.x;
  const dy = p3.y - p0.y;
  const d = Math.hypot(dx, dy) || 1;
  const distTo = (p: Vec2) => Math.abs((p.x - p0.x) * dy - (p.y - p0.y) * dx) / d;
  return Math.max(distTo(p1), distTo(p2));
}

function sampleBezier(p0: Vec2, p1: Vec2, p2: Vec2, p3: Vec2, out: Vec2[]) {
  const rec = (t0: number, t1: number, depth: number) => {
    const a = bezierPoint(p0, p1, p2, p3, t0);
    const b = bezierPoint(p0, p1, p2, p3, t1);
    const segLen = dist(a, b);
    const flat = hullFlatness(
      a,
      bezierPoint(p0, p1, p2, p3, t0 + (t1 - t0) / 3),
      bezierPoint(p0, p1, p2, p3, t0 + (2 * (t1 - t0)) / 3),
      b,
    );
    const accept = flat <= TOL.chord && segLen <= TOL.maxLen;
    if (accept || depth >= TOL.maxDepth || segLen / 2 < TOL.minLen) {
      out.push(b);
      return;
    }
    const tm = (t0 + t1) / 2;
    rec(t0, tm, depth + 1);
    rec(tm, t1, depth + 1);
  };
  out.push(p0);
  rec(0, 1, 0);
}

export function sampleShape(shape: TrackShape): Vec2[] {
  const a = new Map(shape.anchors.map((x) => [x.id, { x: x.x, y: x.y } as Vec2]));
  const pts: Vec2[] = [];
  for (const seg of shape.segments) {
    const from = a.get(seg.from)!;
    const to = a.get(seg.to)!;
    if (seg.type === "line") {
      if (pts.length === 0) pts.push(from);
      pts.push(to);
    } else {
      const local: Vec2[] = [];
      sampleBezier(from, seg.handle_from, seg.handle_to, to, local);
      if (pts.length > 0) local.shift();
      pts.push(...local);
    }
  }
  return pts;
}

export function polylineLength(pts: Vec2[]): number {
  let s = 0;
  for (let i = 1; i < pts.length; i++) s += dist(pts[i - 1], pts[i]);
  return s;
}

export function boundingBox(pts: Vec2[]): { w: number; h: number; minX: number; minY: number } {
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return { w: Math.max(...xs) - minX, h: Math.max(...ys) - minY, minX, minY };
}
