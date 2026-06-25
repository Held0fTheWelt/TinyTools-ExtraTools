import type { TrackShape } from "./shape";
import { dist, norm, type Vec2 } from "../geometry/vec";

type Anchor = TrackShape["anchors"][number];
type Segment = TrackShape["segments"][number];

const EPS = 1e-6;

function v(anchor: Anchor): Vec2 {
  return { x: anchor.x, y: anchor.y };
}

function withZ(p: Vec2) {
  return { x: Number(p.x.toFixed(3)), y: Number(p.y.toFixed(3)), z: 0 };
}

function roundAnchor(anchor: Anchor, p: Vec2): Anchor {
  return { ...anchor, x: Number(p.x.toFixed(3)), y: Number(p.y.toFixed(3)), z: anchor.z ?? 0 };
}

function addScaled(a: Vec2, dir: Vec2, scale: number): Vec2 {
  return { x: a.x + dir.x * scale, y: a.y + dir.y * scale };
}

function orderedAnchorIds(shape: TrackShape): string[] {
  if (shape.segments.length === 0) return shape.anchors.map((a) => a.id);
  const ids = [shape.segments[0].from, ...shape.segments.map((s) => s.to)];
  if (shape.closed && ids.length > 1 && ids[0] === ids[ids.length - 1]) ids.pop();
  return ids;
}

function endpointTangent(current: Vec2, neighbor: Vec2): Vec2 {
  const d = { x: neighbor.x - current.x, y: neighbor.y - current.y };
  return dist(current, neighbor) < EPS ? { x: 1, y: 0 } : norm(d);
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function perpDistance(p: Vec2, a: Vec2, b: Vec2): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < EPS) return dist(p, a);
  const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq));
  return dist(p, { x: a.x + dx * t, y: a.y + dy * t });
}

function turnAngle(prev: Vec2, cur: Vec2, next: Vec2): number {
  const a = norm({ x: cur.x - prev.x, y: cur.y - prev.y });
  const b = norm({ x: next.x - cur.x, y: next.y - cur.y });
  const dot = Math.max(-1, Math.min(1, a.x * b.x + a.y * b.y));
  return (Math.acos(dot) * 180) / Math.PI;
}

function neighborIndex(index: number, offset: number, count: number, closed: boolean): number | null {
  const next = index + offset;
  if (closed) return (next + count) % count;
  return next < 0 || next >= count ? null : next;
}

function segmentLengths(anchors: Anchor[], closed: boolean): number[] {
  const lengths: number[] = [];
  const count = closed ? anchors.length : anchors.length - 1;
  for (let i = 0; i < count; i++) {
    const next = (i + 1) % anchors.length;
    lengths.push(dist(v(anchors[i]), v(anchors[next])));
  }
  return lengths.filter((x) => x > EPS);
}

function shouldRemoveAnchor(anchors: Anchor[], index: number, closed: boolean, medianLength: number): boolean {
  const prevIndex = neighborIndex(index, -1, anchors.length, closed);
  const nextIndex = neighborIndex(index, 1, anchors.length, closed);
  if (prevIndex == null || nextIndex == null) return false;

  const prev = v(anchors[prevIndex]);
  const cur = v(anchors[index]);
  const next = v(anchors[nextIndex]);
  const before = dist(prev, cur);
  const after = dist(cur, next);
  const chord = dist(prev, next);
  const off = perpDistance(cur, prev, next);
  const turn = turnAngle(prev, cur, next);
  const minAdj = Math.min(before, after);
  const maxAdj = Math.max(before, after);

  const tinySegment = minAdj < Math.max(0.2, medianLength * 0.06);
  const redundant = off <= Math.max(0.25, medianLength * 0.035) && turn <= 12;
  const shortSpike = minAdj < medianLength * 0.22 && turn > 25 && chord > maxAdj * 0.75;
  return tinySegment || redundant || shortSpike;
}

function cleanAnchors(shape: TrackShape, strength: number): { anchors: Anchor[]; removed: number; moved: number } {
  const ids = orderedAnchorIds(shape);
  const byId = new Map(shape.anchors.map((a) => [a.id, a]));
  let anchors = ids.map((id) => byId.get(id)).filter(Boolean) as Anchor[];
  const minCount = shape.closed ? 3 : 2;
  if (anchors.length <= minCount) return { anchors, removed: 0, moved: 0 };

  let removed = 0;
  for (let pass = 0; pass < 2 && anchors.length > minCount; pass++) {
    const medianLength = median(segmentLengths(anchors, shape.closed));
    if (medianLength <= EPS) break;
    const keep = anchors.map((_, index) => !shouldRemoveAnchor(anchors, index, shape.closed, medianLength));
    if (!shape.closed) {
      keep[0] = true;
      keep[keep.length - 1] = true;
    }
    const next = anchors.filter((_, index) => keep[index]);
    if (next.length < minCount || next.length === anchors.length) break;
    removed += anchors.length - next.length;
    anchors = next;
  }

  const medianLength = median(segmentLengths(anchors, shape.closed));
  let moved = 0;
  if (medianLength > EPS) {
    anchors = anchors.map((anchor, index) => {
      const prevIndex = neighborIndex(index, -1, anchors.length, shape.closed);
      const nextIndex = neighborIndex(index, 1, anchors.length, shape.closed);
      if (prevIndex == null || nextIndex == null) return anchor;

      const prev = v(anchors[prevIndex]);
      const cur = v(anchor);
      const next = v(anchors[nextIndex]);
      const before = dist(prev, cur);
      const after = dist(cur, next);
      const turn = turnAngle(prev, cur, next);
      const protectedCorner = turn >= 75 && before >= medianLength * 0.35 && after >= medianLength * 0.35;
      if (protectedCorner) return anchor;

      const target = { x: (prev.x + next.x) / 2, y: (prev.y + next.y) / 2 };
      const delta = dist(cur, target);
      if (delta <= Math.max(0.05, medianLength * 0.025)) return anchor;

      const maxMove = medianLength * 0.12 * strength;
      const factor = Math.min(0.35 * strength, maxMove / delta);
      const adjusted = { x: cur.x + (target.x - cur.x) * factor, y: cur.y + (target.y - cur.y) * factor };
      if (dist(cur, adjusted) > 0.01) moved += 1;
      return roundAnchor(anchor, adjusted);
    });
  }

  return { anchors, removed, moved };
}

export function smoothTrackShape(shape: TrackShape, strength = 0.85): TrackShape {
  const cleaned = cleanAnchors(shape, Math.max(0, Math.min(1.5, strength)));
  const ids = cleaned.anchors.map((a) => a.id);
  const byId = new Map(cleaned.anchors.map((a) => [a.id, a]));
  const indexById = new Map(ids.map((id, index) => [id, index]));
  const n = ids.length;
  if (n < 2) return shape;

  const tangents = new Map<string, Vec2>();
  const tangentLengths = new Map<string, number>();

  for (let i = 0; i < n; i++) {
    const anchor = byId.get(ids[i]);
    if (!anchor) continue;
    const cur = v(anchor);
    const prev = byId.get(ids[(i - 1 + n) % n]);
    const next = byId.get(ids[(i + 1) % n]);
    let tangent: Vec2;
    let handleLength = 0;

    if (!shape.closed && i === 0 && next) {
      tangent = endpointTangent(cur, v(next));
      handleLength = dist(cur, v(next)) / 3;
    } else if (!shape.closed && i === n - 1 && prev) {
      tangent = endpointTangent(v(prev), cur);
      handleLength = dist(v(prev), cur) / 3;
    } else if (prev && next) {
      const before = dist(v(prev), cur);
      const after = dist(cur, v(next));
      tangent = before < EPS && after < EPS ? { x: 1, y: 0 } : norm({ x: v(next).x - v(prev).x, y: v(next).y - v(prev).y });
      handleLength = Math.min(before, after) * 0.45;
    } else {
      tangent = { x: 1, y: 0 };
    }

    tangents.set(ids[i], tangent);
    tangentLengths.set(ids[i], handleLength * Math.max(0, Math.min(1.5, strength)));
  }

  const baseSegments = shape.closed
    ? ids.map((id, index) => ({ id: `seg_${String(index + 1).padStart(3, "0")}`, from: id, to: ids[(index + 1) % ids.length] }))
    : ids.slice(0, -1).map((id, index) => ({ id: `seg_${String(index + 1).padStart(3, "0")}`, from: id, to: ids[index + 1] }));

  const segments = baseSegments.map((seg): Segment => {
    const from = byId.get(seg.from);
    const to = byId.get(seg.to);
    const fromIndex = indexById.get(seg.from);
    const toIndex = indexById.get(seg.to);
    if (!from || !to || fromIndex == null || toIndex == null) {
      return { id: seg.id, type: "line", from: seg.from, to: seg.to, samples: 1 };
    }

    const p0 = v(from);
    const p3 = v(to);
    const segmentLength = dist(p0, p3);
    if (segmentLength < EPS) return { id: seg.id, type: "line", from: seg.from, to: seg.to, samples: 1 };

    const fromDir = tangents.get(seg.from) ?? endpointTangent(p0, p3);
    const toDir = tangents.get(seg.to) ?? endpointTangent(p0, p3);
    const fromLength = Math.min(segmentLength * 0.45, tangentLengths.get(seg.from) ?? segmentLength / 3);
    const toLength = Math.min(segmentLength * 0.45, tangentLengths.get(seg.to) ?? segmentLength / 3);

    return {
      id: seg.id,
      type: "bezier",
      from: seg.from,
      to: seg.to,
      handle_from: withZ(addScaled(p0, fromDir, fromLength)),
      handle_to: withZ(addScaled(p3, toDir, -toLength)),
      samples: 24,
      adaptive: true,
    };
  });

  return {
    ...shape,
    anchors: cleaned.anchors,
    segments,
    metadata: {
      ...(shape.metadata ?? {}),
      smoothing: {
        method: "cleaned_c1_tangent_handles",
        strength,
        removed_anchor_count: cleaned.removed,
        moved_anchor_count: cleaned.moved,
      },
    },
  };
}
