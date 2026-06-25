import type { TrackShape } from "./shape";
import { mapSegment } from "./edit";

export function toBezier(doc: TrackShape, segId: string): TrackShape {
  const a = new Map(doc.anchors.map((x) => [x.id, x]));
  return mapSegment(doc, segId, (s) => {
    if (s.type === "bezier") return s;
    const p0 = a.get(s.from)!;
    const p3 = a.get(s.to)!;
    const lerpPt = (t: number) => ({
      x: p0.x + (p3.x - p0.x) * t,
      y: p0.y + (p3.y - p0.y) * t,
      z: 0,
    });
    return {
      id: s.id,
      label: s.label,
      type: "bezier",
      from: s.from,
      to: s.to,
      handle_from: lerpPt(1 / 3),
      handle_to: lerpPt(2 / 3),
      samples: s.samples,
      adaptive: true,
    };
  });
}

export function toLine(doc: TrackShape, segId: string): TrackShape {
  return mapSegment(doc, segId, (s) => {
    if (s.type === "line") return s;
    return { id: s.id, label: s.label, type: "line", from: s.from, to: s.to, samples: s.samples };
  });
}
