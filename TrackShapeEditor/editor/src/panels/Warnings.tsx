import type { CSSProperties } from "react";
import type { Diagnostic } from "../validation/topology";

export function Warnings({
  items,
  onSelect,
}: {
  items: Diagnostic[];
  onSelect: (id: string) => void;
}) {
  return (
    <ul data-testid="warnings" style={list}>
      {items.map((d, i) => (
        <li key={i} data-severity={d.severity} style={item}>
          <button type="button" style={button} onClick={() => d.targetId && onSelect(d.targetId)}>
            {d.message}
          </button>
        </li>
      ))}
    </ul>
  );
}

const list: CSSProperties = {
  listStyle: "none",
  margin: 0,
  padding: 8,
  display: "grid",
  gap: 4,
};

const item: CSSProperties = {
  minWidth: 0,
};

const button: CSSProperties = {
  maxWidth: "100%",
  textAlign: "left",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
};
