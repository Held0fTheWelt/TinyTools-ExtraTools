import type { TrackShape } from "../model/shape";
import { type Vec2, sub, norm, angleDeg, dist } from "../geometry/vec";
import { bezierDeriv } from "../geometry/bezier";
import type { Diagnostic } from "./topology";

type Diag = Diagnostic & { angleDeg?: number };

function startDir(s: TrackShape["segments"][number], a: Map<string, Vec2>): Vec2 {
  const from = a.get(s.from)!;
  const to = a.get(s.to)!;
  return s.type === "line" ? norm(sub(to, from)) : norm(bezierDeriv(from, s.handle_from, s.handle_to, to, 0));
}

function endDir(s: TrackShape["segments"][number], a: Map<string, Vec2>): Vec2 {
  const from = a.get(s.from)!;
  const to = a.get(s.to)!;
  return s.type === "line" ? norm(sub(to, from)) : norm(bezierDeriv(from, s.handle_from, s.handle_to, to, 1));
}

export function validateGeometry(doc: TrackShape): Diag[] {
  const out: Diag[] = [];
  const a = new Map(doc.anchors.map((x) => [x.id, { x: x.x, y: x.y } as Vec2]));
  const maxStep = (doc.sampling as Record<string, number>).max_angle_step_deg ?? 5.0;

  for (const s of doc.segments) {
    if (s.type !== "bezier") continue;
    const from = a.get(s.from)!;
    const to = a.get(s.to)!;
    if (dist(from, s.handle_from) < 1e-6 || dist(to, s.handle_to) < 1e-6)
      out.push({
        code: "degenerate_handle",
        severity: "warning",
        targetId: s.id,
        message: `Segment "${s.id}" has a handle coincident with its anchor.`,
      });
  }

  const segs = doc.segments;
  const joins = doc.closed ? segs.length : segs.length - 1;
  for (let i = 0; i < joins; i++) {
    const cur = segs[i];
    const next = segs[(i + 1) % segs.length];
    const ang = angleDeg(endDir(cur, a), startDir(next, a));
    if (ang > maxStep)
      out.push({
        code: "sharp_corner",
        severity: "warning",
        targetId: cur.id,
        angleDeg: ang,
        message: `Sharp corner at ${cur.to}: angle step ${ang.toFixed(1)}°, recommended <= ${maxStep.toFixed(1)}°.`,
      });
  }

  return out;
}
