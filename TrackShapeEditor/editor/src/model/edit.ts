import type { TrackShape } from "./shape";

type Anchor = TrackShape["anchors"][number];
type Segment = TrackShape["segments"][number];

export type HandleRef = { segId: string; end: "from" | "to" };

export function mapAnchor(doc: TrackShape, id: string, fn: (a: Anchor) => Anchor): TrackShape {
  return { ...doc, anchors: doc.anchors.map((a) => (a.id === id ? fn(a) : a)) };
}

export function mapSegment(doc: TrackShape, id: string, fn: (s: Segment) => Segment): TrackShape {
  return { ...doc, segments: doc.segments.map((s) => (s.id === id ? fn(s) : s)) };
}

export function incidentBezierHandles(doc: TrackShape, anchorId: string): HandleRef[] {
  const out: HandleRef[] = [];
  for (const s of doc.segments) {
    if (s.type !== "bezier") continue;
    if (s.from === anchorId) out.push({ segId: s.id, end: "from" });
    if (s.to === anchorId) out.push({ segId: s.id, end: "to" });
  }
  return out;
}

export function handlePos(seg: Segment, end: "from" | "to") {
  if (seg.type !== "bezier") throw new Error("not a bezier");
  return end === "from" ? seg.handle_from : seg.handle_to;
}

export function setHandle(doc: TrackShape, segId: string, end: "from" | "to", x: number, y: number): TrackShape {
  return mapSegment(doc, segId, (s) => {
    if (s.type !== "bezier") return s;
    const h = { ...(end === "from" ? s.handle_from : s.handle_to), x, y };
    return end === "from" ? { ...s, handle_from: h } : { ...s, handle_to: h };
  });
}
