import { useState } from "react";
import type { TrackShape } from "../model/shape";
import { mapAnchor, mapSegment } from "../model/edit";
import { renameAnchor } from "../model/rename";
import { toBezier, toLine } from "../model/convert";

export type Selection = { kind: "anchor"; id: string } | { kind: "segment"; id: string } | null;

export function Inspector({
  doc,
  selection,
  onChange,
}: {
  doc: TrackShape;
  selection: Selection;
  onChange: (next: TrackShape) => void;
}) {
  const [idError, setIdError] = useState<string | null>(null);

  if (!selection) return <div data-testid="inspector" />;

  if (selection.kind === "segment") {
    const s = doc.segments.find((x) => x.id === selection.id)!;
    const adaptive = s.type === "bezier" && s.adaptive === true;
    return (
      <div data-testid="inspector">
        <label>
          ID <input value={s.id} readOnly />
        </label>
        <label>
          Type <input value={s.type} readOnly />
        </label>
        <label>
          From <input value={s.from} readOnly />
        </label>
        <label>
          To <input value={s.to} readOnly />
        </label>
        <label>
          Samples{" "}
          <input
            aria-label="samples"
            type="number"
            disabled={adaptive}
            value={s.samples ?? 24}
            onChange={(e) => onChange(mapSegment(doc, s.id, (x) => ({ ...x, samples: +e.target.value })))}
          />
        </label>
        {adaptive && <span>(floor only — adaptive)</span>}
        {s.type === "bezier" && (
          <label>
            <input
              type="checkbox"
              checked={s.adaptive === true}
              onChange={(e) => onChange(mapSegment(doc, s.id, (x) => ({ ...x, adaptive: e.target.checked })))}
            />{" "}
            Adaptive
          </label>
        )}
        {s.type === "line" && (
          <button type="button" onClick={() => onChange(toBezier(doc, s.id))}>
            To Bezier
          </button>
        )}
        {s.type === "bezier" && (
          <button type="button" onClick={() => onChange(toLine(doc, s.id))}>
            To Line
          </button>
        )}
      </div>
    );
  }

  const a = doc.anchors.find((x) => x.id === selection.id)!;

  return (
    <div data-testid="inspector">
      <label>
        ID{" "}
        <input
          defaultValue={a.id}
          onBlur={(e) => {
            try {
              setIdError(null);
              onChange(renameAnchor(doc, a.id, e.target.value));
            } catch (err) {
              setIdError((err as Error).message);
            }
          }}
        />
      </label>
      {idError && <span role="alert">{idError}</span>}
      <label>
        X{" "}
        <input
          type="number"
          value={a.x}
          onChange={(e) => onChange(mapAnchor(doc, a.id, (x) => ({ ...x, x: +e.target.value })))}
        />
      </label>
      <label>
        Y{" "}
        <input
          type="number"
          value={a.y}
          onChange={(e) => onChange(mapAnchor(doc, a.id, (x) => ({ ...x, y: +e.target.value })))}
        />
      </label>
      <label>
        Label{" "}
        <input
          value={a.label ?? ""}
          onChange={(e) => onChange(mapAnchor(doc, a.id, (x) => ({ ...x, label: e.target.value })))}
        />
      </label>
    </div>
  );
}
