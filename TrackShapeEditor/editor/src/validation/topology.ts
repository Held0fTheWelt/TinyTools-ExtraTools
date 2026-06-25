import type { TrackShape } from "../model/shape";
import { dist } from "../geometry/vec";

export interface Diagnostic {
  code: string;
  severity: "error" | "warning";
  targetId?: string;
  message: string;
}

export function validateTopology(doc: TrackShape): Diagnostic[] {
  const out: Diagnostic[] = [];
  const seen = new Set<string>();

  for (const a of doc.anchors) {
    if (seen.has(a.id))
      out.push({
        code: "duplicate_anchor_id",
        severity: "error",
        targetId: a.id,
        message: `Duplicate anchor id "${a.id}".`,
      });
    seen.add(a.id);
  }

  const segIds = new Set<string>();
  for (const s of doc.segments) {
    if (segIds.has(s.id))
      out.push({
        code: "duplicate_segment_id",
        severity: "error",
        targetId: s.id,
        message: `Duplicate segment id "${s.id}".`,
      });
    segIds.add(s.id);
  }

  const anchors = new Map(doc.anchors.map((a) => [a.id, a]));
  for (const s of doc.segments) {
    for (const ref of [s.from, s.to]) {
      if (!anchors.has(ref))
        out.push({
          code: "missing_anchor_ref",
          severity: "error",
          targetId: s.id,
          message: `Segment "${s.id}" references missing anchor "${ref}".`,
        });
    }
    const a = anchors.get(s.from);
    const b = anchors.get(s.to);
    if (a && b && dist(a, b) < 1e-6)
      out.push({
        code: "zero_length_segment",
        severity: "error",
        targetId: s.id,
        message: `Segment "${s.id}" has zero length.`,
      });
  }

  for (let i = 0; i < doc.segments.length - 1; i++) {
    if (doc.segments[i].to !== doc.segments[i + 1].from)
      out.push({
        code: "chain_disconnected",
        severity: "error",
        targetId: doc.segments[i + 1].id,
        message: `Segment "${doc.segments[i + 1].id}" does not continue from the previous segment.`,
      });
  }

  if (doc.closed && doc.segments.length > 0) {
    const first = doc.segments[0];
    const last = doc.segments[doc.segments.length - 1];
    const fa = anchors.get(first.from);
    const la = anchors.get(last.to);
    if (last.to !== first.from && fa && la && dist(fa, la) > 0.05)
      out.push({
        code: "open_seam",
        severity: "error",
        targetId: last.id,
        message: `Closed track seam gap ${dist(fa, la).toFixed(2)} m exceeds 0.05 m.`,
      });
  }

  return out;
}
