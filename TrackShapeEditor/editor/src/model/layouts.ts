import type { TrackShape, TrackShapeLayout } from "./shape";

export type ResolvedTrackLayout = {
  id: string;
  label: string;
  kind: "main_track" | TrackShapeLayout["kind"];
  isMain: boolean;
  shape: TrackShape;
};

function withoutLayouts(doc: TrackShape): Omit<TrackShape, "layouts"> {
  const { layouts: _layouts, ...base } = doc;
  return base;
}

export function resolveTrackLayouts(doc: TrackShape): ResolvedTrackLayout[] {
  const base = withoutLayouts(doc);
  const layouts: ResolvedTrackLayout[] = [
    {
      id: "Main",
      label: doc.name || "Main Track",
      kind: "main_track",
      isMain: true,
      shape: base,
    },
  ];

  for (const layout of doc.layouts ?? []) {
    if (layout.enabled === false) continue;
    layouts.push({
      id: layout.id,
      label: layout.label ?? layout.id,
      kind: layout.kind,
      isMain: false,
      shape: {
        ...base,
        name: layout.label ?? `${doc.name} - ${layout.id}`,
        closed: layout.closed,
        anchors: layout.anchors,
        segments: layout.segments,
        metadata: { ...(doc.metadata ?? {}), ...(layout.metadata ?? {}) },
      },
    });
  }
  return layouts;
}

export function getMainTrackShape(doc: TrackShape): TrackShape {
  return resolveTrackLayouts(doc)[0].shape;
}

