import type { TrackShape } from "./shape";

export function renameAnchor(doc: TrackShape, oldId: string, newId: string): TrackShape {
  if (!/^[a-z0-9_]+$/.test(newId)) throw new Error(`invalid id: ${newId}`);
  if (doc.anchors.some((a) => a.id === newId)) throw new Error(`duplicate id: ${newId}`);
  return {
    ...doc,
    anchors: doc.anchors.map((a) => (a.id === oldId ? { ...a, id: newId } : a)),
    segments: doc.segments.map((s) => ({
      ...s,
      from: s.from === oldId ? newId : s.from,
      to: s.to === oldId ? newId : s.to,
    })),
  };
}
