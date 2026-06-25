import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { parseTrackShape, type TrackShape } from "./model/shape";
import { Viewport } from "./render/Viewport";
import { Metrics } from "./panels/Metrics";
import { Toolbar } from "./panels/Toolbar";
import { Inspector, type Selection } from "./panels/Inspector";
import { TrackTree } from "./panels/TrackTree";
import { Warnings } from "./panels/Warnings";
import { ImportImageDialog } from "./panels/ImportImageDialog";
import { CommandStack } from "./state/commands";
import { moveAnchorTo } from "./state/anchorCommands";
import { moveHandle } from "./state/handleCommands";
import { validateTopology } from "./validation/topology";
import { validateGeometry } from "./validation/geometry";
import { meshPieceEstimate } from "./validation/mesh";
import { sampleShape, polylineLength } from "./geometry/metrics";
import type { ReferenceImageLayer } from "./io/referenceImage";
import { getUnrealApplyClient } from "./io/unrealClient";
import example from "../test/fixtures/daytona_shape.example.json";

function findSelection(doc: TrackShape, id: string): Selection {
  if (doc.anchors.some((a) => a.id === id)) return { kind: "anchor", id };
  if (doc.segments.some((s) => s.id === id)) return { kind: "segment", id };
  return null;
}

export default function App() {
  const stackRef = useRef(new CommandStack<TrackShape>(parseTrackShape(example)));
  const [, tick] = useState(0);
  const forceUpdate = () => tick((n) => n + 1);

  const stack = stackRef.current;
  const doc = stack.state;

  const [selection, setSelection] = useState<Selection>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [fileName, setFileName] = useState("daytona_shape.example.json");
  const [showMeshTicks, setShowMeshTicks] = useState(true);
  const [showScalePreview, setShowScalePreview] = useState(true);
  const [importing, setImporting] = useState(false);
  const [referenceImage, setReferenceImage] = useState<ReferenceImageLayer | null>(null);
  const [unrealActorName, setUnrealActorName] = useState("BP_GeneratedTrackSpline");
  const [unrealHost, setUnrealHost] = useState("127.0.0.1");
  const [unrealPort, setUnrealPort] = useState("8732");
  const [unrealReplace, setUnrealReplace] = useState(false);
  const [unrealCreateMesh, setUnrealCreateMesh] = useState(false);
  const [unrealBusy, setUnrealBusy] = useState(false);
  const [unrealStatus, setUnrealStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const diagnostics = useMemo(() => [...validateTopology(doc), ...validateGeometry(doc)], [doc]);

  const pieceLengthM = (doc.mesh as { piece_length_m?: number }).piece_length_m ?? 20;
  const pts = useMemo(() => sampleShape(doc), [doc]);
  const rawLen = polylineLength(pts);
  const meshPieces = meshPieceEstimate(rawLen, pieceLengthM);

  const applyToUnreal = useCallback(async () => {
    setUnrealStatus(null);
    const port = Number(unrealPort);
    if (!Number.isInteger(port) || port <= 0 || port > 65535) {
      setUnrealStatus({ kind: "error", text: "Invalid Unreal port." });
      return;
    }
    setUnrealBusy(true);
    try {
      const result = await getUnrealApplyClient().apply({
        shape: doc,
        actorName: unrealActorName.trim() || "BP_GeneratedTrackSpline",
        host: unrealHost.trim() || "127.0.0.1",
        port,
        replace: unrealReplace,
        createRoadMesh: unrealCreateMesh,
        meshPieceLengthM: pieceLengthM,
      });
      if (result.error) throw new Error(result.error);
      const actor = result.actor ?? unrealActorName;
      const points = result.point_count ?? 0;
      const layoutText = result.layout_count && result.layout_count > 1 ? `, ${result.layout_count} layouts` : "";
      const meshText = result.mesh_piece_count != null ? `, ${result.mesh_piece_count} mesh pieces` : "";
      setUnrealStatus({ kind: "ok", text: `Sent ${points} main points to ${actor}${layoutText}${meshText}.` });
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setUnrealStatus({
        kind: "error",
        text: /Failed to fetch|NetworkError|ECONNREFUSED|timed out|refused|not reachable|WinError 10061/i.test(msg)
          ? "Unreal MCP is not reachable."
          : msg,
      });
    } finally {
      setUnrealBusy(false);
    }
  }, [doc, pieceLengthM, unrealActorName, unrealCreateMesh, unrealHost, unrealPort, unrealReplace]);

  const dragAnchorStart = useRef<{ id: string; x: number; y: number } | null>(null);
  const dragHandleStart = useRef<{ segId: string; end: "from" | "to"; x: number; y: number } | null>(null);

  const onAnchorDrag = useCallback(
    (id: string, w: { x: number; y: number }, _mirror: boolean) => {
      if (!dragAnchorStart.current || dragAnchorStart.current.id !== id) {
        dragAnchorStart.current = { id, x: w.x, y: w.y };
        return;
      }
      const start = dragAnchorStart.current;
      const dx = w.x - start.x;
      const dy = w.y - start.y;
      if (dx === 0 && dy === 0) return;
      stack.run(moveAnchorTo(doc, id, doc.anchors.find((a) => a.id === id)!.x + dx, doc.anchors.find((a) => a.id === id)!.y + dy));
      dragAnchorStart.current = { id, x: w.x, y: w.y };
      forceUpdate();
    },
    [doc, stack],
  );

  const onHandleDrag = useCallback(
    (segId: string, end: "from" | "to", w: { x: number; y: number }, mirror: boolean) => {
      if (!dragHandleStart.current || dragHandleStart.current.segId !== segId || dragHandleStart.current.end !== end) {
        dragHandleStart.current = { segId, end, x: w.x, y: w.y };
        return;
      }
      stack.run(moveHandle(doc, segId, end, w, mirror));
      dragHandleStart.current = { segId, end, x: w.x, y: w.y };
      forceUpdate();
    },
    [doc, stack],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "z") {
        e.preventDefault();
        stack.undo();
        forceUpdate();
      }
      if (e.ctrlKey && e.key === "y") {
        e.preventDefault();
        stack.redo();
        forceUpdate();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stack]);

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto minmax(0, 1fr) minmax(96px, 22vh)", height: "100vh" }}>
      <Toolbar
        stack={stack}
        fileName={fileName}
        onOpen={(d) => {
          stackRef.current = new CommandStack(d);
          setReferenceImage(null);
          forceUpdate();
        }}
        onFileNameChange={setFileName}
        onImportImage={() => setImporting(true)}
        onApplyUnreal={() => void applyToUnreal()}
        applyBusy={unrealBusy}
      />
      <div style={{ display: "grid", gridTemplateColumns: "260px minmax(0, 1fr) 240px", minHeight: 0, minWidth: 0 }}>
        <TrackTree doc={doc} selection={selection} onSelect={setSelection} />
        <Viewport
          shape={doc}
          focusId={focusId}
          showMeshTicks={showMeshTicks}
          pieceLengthM={pieceLengthM}
          showScalePreview={showScalePreview}
          referenceImage={referenceImage}
          onAnchorDrag={onAnchorDrag}
          onHandleDrag={onHandleDrag}
          onSelectAnchor={(id) => setSelection({ kind: "anchor", id })}
          onSelectSegment={(id) => setSelection({ kind: "segment", id })}
        />
        <div style={{ overflow: "auto", padding: 8, minHeight: 0 }}>
          <Inspector
            doc={doc}
            selection={selection}
            onChange={(next) => {
              stackRef.current = new CommandStack(next);
              forceUpdate();
            }}
          />
          <div style={{ marginTop: 12 }}>
            <label>
              <input type="checkbox" checked={showMeshTicks} onChange={(e) => setShowMeshTicks(e.target.checked)} /> Mesh
              ticks
            </label>
            <div>Mesh pieces: ~{meshPieces}</div>
            <label>
              <input
                type="checkbox"
                checked={showScalePreview}
                onChange={(e) => setShowScalePreview(e.target.checked)}
              />{" "}
              Scale preview
            </label>
          </div>
          <div style={{ marginTop: 12, borderTop: "1px solid #ddd", paddingTop: 10, display: "grid", gap: 8 }}>
            <strong>Unreal MCP</strong>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Actor</span>
              <input value={unrealActorName} onChange={(e) => setUnrealActorName(e.target.value)} />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 72px", gap: 6 }}>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Host</span>
                <input value={unrealHost} onChange={(e) => setUnrealHost(e.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Port</span>
                <input value={unrealPort} onChange={(e) => setUnrealPort(e.target.value)} />
              </label>
            </div>
            <label>
              <input type="checkbox" checked={unrealReplace} onChange={(e) => setUnrealReplace(e.target.checked)} /> Replace
            </label>
            <label>
              <input
                type="checkbox"
                checked={unrealCreateMesh}
                onChange={(e) => setUnrealCreateMesh(e.target.checked)}
              />{" "}
              Road mesh
            </label>
            <button type="button" onClick={() => void applyToUnreal()} disabled={unrealBusy}>
              {unrealBusy ? "Sending..." : "Send to Unreal"}
            </button>
            {unrealStatus && (
              <div
                role={unrealStatus.kind === "error" ? "alert" : "status"}
                style={{ color: unrealStatus.kind === "error" ? "#b00020" : "#146c43", fontSize: 12 }}
              >
                {unrealStatus.text}
              </div>
            )}
          </div>
          {referenceImage && (
            <div style={{ marginTop: 12, borderTop: "1px solid #ddd", paddingTop: 10 }}>
              <label>
                <input
                  type="checkbox"
                  checked={referenceImage.visible}
                  onChange={(e) => setReferenceImage({ ...referenceImage, visible: e.target.checked })}
                />{" "}
                Reference image
              </label>
              <label style={{ display: "grid", gap: 4, marginTop: 8 }}>
                <span>Opacity {Math.round(referenceImage.opacity * 100)}%</span>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={referenceImage.opacity}
                  onChange={(e) => setReferenceImage({ ...referenceImage, opacity: Number(e.target.value) })}
                />
              </label>
              <button type="button" style={{ marginTop: 8 }} onClick={() => setReferenceImage(null)}>
                Remove
              </button>
            </div>
          )}
        </div>
      </div>
      <div style={{ borderTop: "1px solid #ccc", overflow: "auto", minHeight: 0, background: "#fff" }}>
        <Metrics shape={doc} />
        <Warnings
          items={diagnostics}
          onSelect={(id) => {
            setFocusId(id);
            setSelection(findSelection(doc, id));
          }}
        />
      </div>
      {importing && (
        <ImportImageDialog
          onClose={() => setImporting(false)}
          onImport={(shape, name, reference) => {
            stackRef.current = new CommandStack(shape);
            setFileName(name);
            setReferenceImage(reference ?? null);
            setSelection(null);
            setFocusId(null);
            setImporting(false);
            forceUpdate();
          }}
        />
      )}
    </div>
  );
}
