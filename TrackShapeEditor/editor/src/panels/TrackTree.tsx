import type { CSSProperties } from "react";
import type { TrackShape } from "../model/shape";
import type { Selection } from "./Inspector";
import { resolveTrackLayouts } from "../model/layouts";

export function TrackTree({
  doc,
  selection,
  onSelect,
}: {
  doc: TrackShape;
  selection: Selection;
  onSelect: (sel: Selection) => void;
}) {
  const layouts = resolveTrackLayouts(doc);
  return (
    <nav data-testid="track-tree" aria-label="Track navigation" style={panel}>
      <h3 style={heading}>Layouts</h3>
      <ul style={list}>
        {layouts.map((layout) => (
          <li key={layout.id} style={item}>
            <button type="button" data-layout={layout.id} style={button} disabled={!layout.isMain}>
              {layout.label} ({layout.kind})
            </button>
          </li>
        ))}
      </ul>
      <h3 style={heading}>Anchors</h3>
      <ul style={list}>
        {doc.anchors.map((a) => (
          <li key={a.id} style={item}>
            <button
              type="button"
              data-selected={selection?.kind === "anchor" && selection.id === a.id}
              style={button}
              onClick={() => onSelect({ kind: "anchor", id: a.id })}
            >
              {a.label ?? a.id}
            </button>
          </li>
        ))}
      </ul>
      <h3 style={heading}>Segments</h3>
      <ul style={list}>
        {doc.segments.map((s) => (
          <li key={s.id} style={item}>
            <button
              type="button"
              data-selected={selection?.kind === "segment" && selection.id === s.id}
              style={button}
              onClick={() => onSelect({ kind: "segment", id: s.id })}
            >
              {s.label ?? s.id} ({s.type})
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

const panel: CSSProperties = {
  minHeight: 0,
  height: "100%",
  overflowY: "auto",
  overflowX: "hidden",
  scrollbarGutter: "stable",
  boxSizing: "border-box",
  padding: "10px 8px",
  borderRight: "1px solid #d8d8d8",
  background: "#fbfbfb",
};

const heading: CSSProperties = {
  margin: "8px 0 6px",
  fontSize: 13,
  lineHeight: 1.2,
};

const list: CSSProperties = {
  listStyle: "none",
  margin: 0,
  padding: 0,
};

const item: CSSProperties = {
  marginBottom: 4,
};

const button: CSSProperties = {
  width: "100%",
  minHeight: 28,
  textAlign: "left",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};
