import { useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent, type PointerEvent } from "react";
import { parseTrackShape, type TrackShape } from "../model/shape";
import { getTraceClient, type TraceClient, type TraceRequest } from "../io/traceClient";
import { referenceImageFromShape, type ReferenceImageLayer } from "../io/referenceImage";
import { sampleShape } from "../geometry/metrics";
import { smoothTrackShape } from "../model/smooth";
import {
  componentAt,
  detectComponents,
  drawComponentOverlay,
  maskColorToDataUrl,
  maskComponentToDataUrl,
  type ComponentDetection,
} from "../io/componentSelection";

type Props = {
  onImport: (shape: TrackShape, fileName: string, referenceImage?: ReferenceImageLayer | null) => void;
  onClose: () => void;
  /** Injectable for tests; defaults to the auto-detected transport (HTTP or Tauri). */
  client?: TraceClient;
};

type TraceHint = { x: number; y: number };

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const reader = new FileReader();
    reader.onload = () => res(String(reader.result));
    reader.onerror = () => rej(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(file);
  });
}

function parseHexColor(value: string): [number, number, number] | null {
  const m = value.trim().match(/^#?([0-9a-f]{6})$/i);
  if (!m) return null;
  const hex = m[1];
  return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];
}

function normalizedHex(value: string): string {
  const m = value.trim().match(/^#?([0-9a-f]{6})$/i);
  return m ? `#${m[1].toLowerCase()}` : "#ed1c24";
}

export function ImportImageDialog({ onImport, onClose, client }: Props) {
  const traceClient = client ?? getTraceClient();
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileRun = useRef(0);
  const detectionRun = useRef(0);
  const [file, setFile] = useState<File | null>(null);
  const [imageDataUrl, setImageDataUrl] = useState<string | null>(null);
  const [detection, setDetection] = useState<ComponentDetection | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [hoveredComponent, setHoveredComponent] = useState<number | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<number | null>(null);
  const [includePitLane, setIncludePitLane] = useState(false);
  const [pitLaneComponent, setPitLaneComponent] = useState<number | null>(null);
  const [targetLen, setTargetLen] = useState("4023");
  const [useTrackColor, setUseTrackColor] = useState(true);
  const [advanced, setAdvanced] = useState(false);
  const [trackColor, setTrackColor] = useState("#ed1c24");
  const [bgColor, setBgColor] = useState("");
  const [tolerance, setTolerance] = useState("80");
  const [previewing, setPreviewing] = useState(false);
  const [previewShape, setPreviewShape] = useState<TrackShape | null>(null);
  const [traceHints, setTraceHints] = useState<TraceHint[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas || !detection) return;
    drawComponentOverlay(canvas, detection, hoveredComponent, selectedComponent);
  }, [detection, hoveredComponent, selectedComponent]);

  useEffect(() => {
    const run = ++detectionRun.current;
    setDetection(null);
    setHoveredComponent(null);
    setSelectedComponent(null);
    setTraceHints([]);
    if (!imageDataUrl) return;

    const color = useTrackColor ? parseHexColor(trackColor) : null;
    const tol = Number(tolerance) || 80;
    setDetecting(true);
    detectComponents(imageDataUrl, { targetColor: color, tolerance: tol })
      .then((nextDetection) => {
        if (run !== detectionRun.current) return;
        setDetection(nextDetection);
        setSelectedComponent(nextDetection.components[0]?.id ?? null);
        setPitLaneComponent(nextDetection.components[1]?.id ?? null);
      })
      .catch((e) => {
        if (run !== detectionRun.current) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (run === detectionRun.current) setDetecting(false);
      });
  }, [imageDataUrl, trackColor, tolerance, useTrackColor]);

  useEffect(() => {
    setTraceHints([]);
    setPreviewShape(null);
  }, [advanced, bgColor, imageDataUrl, includePitLane, pitLaneComponent, selectedComponent, tolerance, trackColor, useTrackColor]);

  useEffect(() => {
    setPreviewShape(null);
  }, [targetLen, traceHints]);

  const handleFile = async (nextFile: File | null) => {
    const run = ++fileRun.current;
    setFile(nextFile);
    setImageDataUrl(null);
    setDetection(null);
    setHoveredComponent(null);
    setSelectedComponent(null);
    setTraceHints([]);
    setError(null);
    if (!nextFile) return;

    try {
      const url = await fileToDataUrl(nextFile);
      if (run !== fileRun.current) return;
      setImageDataUrl(url);
    } catch (e) {
      if (run !== fileRun.current) return;
      setError(e instanceof Error ? e.message : String(e));
      setDetecting(false);
    }
  };

  const componentFromPointer = (e: MouseEvent<HTMLDivElement> | PointerEvent<HTMLDivElement>) => {
    if (!detection) return null;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * detection.width;
    const y = ((e.clientY - rect.top) / rect.height) * detection.height;
    return componentAt(detection, x, y) || null;
  };

  const imagePixelSize = useMemo(() => {
    if (detection) return { width: detection.width, height: detection.height };
    const size = (previewShape?.metadata as { import?: { image_size_px?: unknown } } | undefined)?.import?.image_size_px;
    if (Array.isArray(size) && Number(size[0]) > 0 && Number(size[1]) > 0) {
      return { width: Number(size[0]), height: Number(size[1]) };
    }
    return null;
  }, [detection, previewShape]);

  const imagePointFromPointer = (e: MouseEvent<HTMLDivElement> | PointerEvent<HTMLDivElement>): TraceHint | null => {
    if (!imagePixelSize) return null;
    const rect = e.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    return {
      x: ((e.clientX - rect.left) / rect.width) * imagePixelSize.width,
      y: ((e.clientY - rect.top) / rect.height) * imagePixelSize.height,
    };
  };

  const buildTraceRequest = async (
    hints: TraceHint[] = traceHints,
    componentId: number | null = selectedComponent,
    overrides: Partial<TraceRequest> = {},
  ) => {
    if (!file) throw new Error("Please choose an image first.");
    const t = Number(targetLen);
    if (!Number.isFinite(t) || t <= 0) {
      throw new Error("Target length must be a number greater than 0.");
    }
    const originalImageDataUrl = imageDataUrl ?? (await fileToDataUrl(file));
    const color = useTrackColor ? parseHexColor(trackColor) : null;
    const tol = Number(tolerance) || 80;
    const traceImageDataUrl =
      detection && componentId
        ? await maskComponentToDataUrl(originalImageDataUrl, detection, componentId)
        : color
          ? await maskColorToDataUrl(originalImageDataUrl, color, tol)
          : originalImageDataUrl;
    const usesMask = traceImageDataUrl !== originalImageDataUrl;
    const req: TraceRequest = {
      image_b64: traceImageDataUrl,
      filename: file.name,
      target_length_m: t,
      tolerance: 50,
      track_color: "#141414",
      background_color: "#ffffff",
      ...overrides,
    };
    if (!usesMask) {
      req.tolerance = Number(tolerance) || 40;
      delete req.track_color;
      delete req.background_color;
      if (advanced && bgColor.trim()) req.background_color = bgColor.trim();
    }
    if (hints.length) {
      req.guide_points_px = hints.map((p) => ({ x: Number(p.x.toFixed(2)), y: Number(p.y.toFixed(2)) }));
    }
    return { originalImageDataUrl, req };
  };

  const traceComponentShape = async (
    componentId: number | null,
    hints: TraceHint[],
    overrides: Partial<TraceRequest> = {},
  ) => {
    const { req } = await buildTraceRequest(hints, componentId, overrides);
    const result = await traceClient.trace(req);
    if (result.error) throw new Error(result.error);
    return parseTrackShape(result.shape);
  };

  const importMetersPerPixel = (shape: TrackShape): number | null => {
    const value = (shape.metadata as { import?: { image_transform?: { m_per_px?: unknown } } } | undefined)?.import
      ?.image_transform?.m_per_px;
    const mpp = Number(value);
    return Number.isFinite(mpp) && mpp > 0 ? mpp : null;
  };

  const withPitLaneLayout = (main: TrackShape, pit: TrackShape): TrackShape =>
    parseTrackShape({
      ...main,
      layouts: [
        ...(main.layouts ?? []),
        {
          id: "PitLane",
          label: "Pit Lane",
          kind: "pit_lane",
          closed: pit.closed,
          anchors: pit.anchors,
          segments: pit.segments,
          metadata: {
            source: "image_trace",
            import: (pit.metadata as { import?: unknown } | undefined)?.import,
          },
        },
      ],
      metadata: {
        ...(main.metadata ?? {}),
        multi_layout_import: {
          pit_lane_component_id: pitLaneComponent,
          main_component_id: selectedComponent,
        },
      },
    });

  const buildImportedShape = async (hints: TraceHint[] = traceHints) => {
    const usePitLane =
      includePitLane &&
      detection &&
      pitLaneComponent != null &&
      pitLaneComponent > 0 &&
      pitLaneComponent !== selectedComponent;
    const main = await traceComponentShape(selectedComponent, hints, usePitLane ? { origin: "image" } : {});
    if (!usePitLane) return main;

    const mpp = importMetersPerPixel(main);
    if (!mpp) throw new Error("Could not read the main track scale.");
    const pit = await traceComponentShape(pitLaneComponent, [], {
      origin: "image",
      meters_per_pixel: mpp,
    });
    return withPitLaneLayout(main, pit);
  };

  const runPreview = async (hints: TraceHint[] = traceHints) => {
    setError(null);
    setPreviewing(true);
    try {
      setPreviewShape(await buildImportedShape(hints));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPreviewing(false);
    }
  };

  const clearTraceHints = () => {
    const next: TraceHint[] = [];
    setTraceHints(next);
    if (previewShape && file) {
      void runPreview(next);
    } else {
      setPreviewShape(null);
    }
  };

  const smoothPreview = () => {
    if (!previewShape) return;
    setError(null);
    try {
      setPreviewShape(parseTrackShape(smoothTrackShape(previewShape)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const previewPolyline = useMemo(() => {
    if (!previewShape || !imagePixelSize) return "";
    const rect = (previewShape.metadata as { import?: { image_transform?: { world_rect?: unknown } } } | undefined)?.import
      ?.image_transform?.world_rect as { x?: number; y?: number; width?: number; height?: number } | undefined;
    if (!rect || !rect.width || !rect.height) return "";
    return sampleShape(previewShape)
      .map((p) => {
        const x = ((p.x - (rect.x ?? 0)) / rect.width!) * imagePixelSize.width;
        const y = imagePixelSize.height - ((p.y - (rect.y ?? 0)) / rect.height!) * imagePixelSize.height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [imagePixelSize, previewShape]);

  const handlePreviewClick = (e: MouseEvent<HTMLDivElement>) => {
    if (previewShape && !previewing) {
      const point = imagePointFromPointer(e);
      if (!point) return;
      const next = [...traceHints, point];
      setTraceHints(next);
      void runPreview(next);
      return;
    }
    const id = componentFromPointer(e);
    if (id) setSelectedComponent(id);
  };

  const submit = async () => {
    setError(null);
    if (!file) {
      setError("Please choose an image first.");
      return;
    }
    const t = Number(targetLen);
    if (!Number.isFinite(t) || t <= 0) {
      setError("Target length must be a number greater than 0.");
      return;
    }
    setBusy(true);
    try {
      const { originalImageDataUrl } = await buildTraceRequest();
      let shape = previewShape;
      if (!shape) {
        shape = await buildImportedShape();
      }
      onImport(
        shape,
        file.name.replace(/\.[^.]+$/, "") + ".json",
        referenceImageFromShape(shape, originalImageDataUrl, file.name),
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(
        /Failed to fetch|NetworkError|ECONNREFUSED/i.test(msg)
          ? "Trace helper is not reachable. It normally starts with the editor automatically; otherwise start it manually with: python serve_trace.py"
          : msg,
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div role="dialog" aria-label="Import image" style={overlay} onClick={onClose}>
      <div style={panel} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: "0 0 4px" }}>Import image</h3>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: "#667" }}>
          Convert the dominant track in the image into a scaled spline.
        </p>

        <label style={row}>
          <span>Image (PNG/JPG)</span>
          <input
            type="file"
            accept="image/png,image/jpeg"
            onChange={(e) => void handleFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label style={{ ...row, cursor: "pointer", userSelect: "none" }}>
          <span>Use track color</span>
          <input type="checkbox" checked={useTrackColor} onChange={(e) => setUseTrackColor(e.target.checked)} />
        </label>

        {useTrackColor && (
          <div style={colorGrid}>
            <label style={compactRow}>
              <span>Color</span>
              <span style={colorControls}>
                <input
                  type="color"
                  value={normalizedHex(trackColor)}
                  onChange={(e) => setTrackColor(e.target.value)}
                />
                <input value={trackColor} onChange={(e) => setTrackColor(e.target.value)} />
              </span>
            </label>
            <label style={compactRow}>
              <span>Tolerance</span>
              <input type="number" min={1} max={255} value={tolerance} onChange={(e) => setTolerance(e.target.value)} />
            </label>
          </div>
        )}

        {imageDataUrl && (
          <div
            style={previewFrame}
            data-testid="image-import-preview"
            onPointerMove={(e) => setHoveredComponent(componentFromPointer(e))}
            onPointerLeave={() => setHoveredComponent(null)}
            onClick={handlePreviewClick}
          >
            <img src={imageDataUrl} alt="" style={previewImage} />
            <canvas ref={overlayCanvasRef} style={previewOverlay} />
            {(previewPolyline || traceHints.length > 0) && imagePixelSize && (
              <svg viewBox={`0 0 ${imagePixelSize.width} ${imagePixelSize.height}`} style={previewOverlay}>
                {previewPolyline && (
                  <>
                    <polyline
                      points={previewPolyline}
                      fill="none"
                      stroke="#00a884"
                      strokeWidth={7}
                      strokeLinecap="round"
                    />
                    <polyline
                      points={previewPolyline}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={2}
                      strokeLinecap="round"
                    />
                  </>
                )}
                {traceHints.map((p, i) => (
                  <g key={`${p.x}:${p.y}:${i}`}>
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r={i === 0 ? 9 : 8}
                      fill={i === 0 ? "#ffd166" : "#ff2fb3"}
                      stroke="#fff"
                      strokeWidth={3}
                    />
                    <circle cx={p.x} cy={p.y} r={3} fill="#111827" />
                  </g>
                ))}
              </svg>
            )}
          </div>
        )}

        {(detecting || detection) && (
          <div style={selectionStatus}>
            <span>{detecting ? "Analyzing regions..." : `${detection?.components.length ?? 0} regions detected`}</span>
            {selectedComponent && <span>Selection #{selectedComponent}</span>}
          </div>
        )}

        {detection && detection.components.length > 1 && (
          <label style={{ ...row, cursor: "pointer", userSelect: "none" }}>
            <span>Pit lane from region #{pitLaneComponent ?? "-"}</span>
            <input
              type="checkbox"
              checked={includePitLane}
              onChange={(e) => setIncludePitLane(e.target.checked)}
            />
          </label>
        )}

        {traceHints.length > 0 && (
          <div style={selectionStatus}>
            <span>Start/seam set - Checkpoints: {Math.max(0, traceHints.length - 1)}</span>
            <button type="button" onClick={clearTraceHints} disabled={previewing || busy}>
              Clear hints
            </button>
          </div>
        )}

        <label style={row}>
          <span>Target length (m)</span>
          <input
            type="number"
            min={1}
            step={1}
            value={targetLen}
            onChange={(e) => setTargetLen(e.target.value)}
          />
        </label>

        <label style={{ ...row, cursor: "pointer", userSelect: "none" }}>
          <span>Advanced (background)</span>
          <input type="checkbox" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
        </label>

        {advanced && (
          <div style={{ paddingLeft: 10, borderLeft: "2px solid #e3e3ea", marginBottom: 4 }}>
            <p style={{ fontSize: 12, color: "#778", margin: "4px 0 8px" }}>
              Optional background value when no color region or selection is used.
            </p>
            <label style={row}>
              <span>Background</span>
              <input placeholder="#ffffff" value={bgColor} onChange={(e) => setBgColor(e.target.value)} />
            </label>
          </div>
        )}

        {error && (
          <p role="alert" style={{ color: "#b00020", fontSize: 13, margin: "8px 0 0" }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
          <button type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="button" onClick={() => void runPreview()} disabled={busy || previewing || !file}>
            {previewing ? "Previewing..." : "Preview"}
          </button>
          <button type="button" onClick={smoothPreview} disabled={busy || previewing || !previewShape}>
            Smooth
          </button>
          <button type="button" onClick={submit} disabled={busy}>
            {busy ? "Tracing..." : "Load"}
          </button>
        </div>
      </div>
    </div>
  );
}

const overlay: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(20,22,28,0.45)",
  display: "grid",
  placeItems: "center",
  zIndex: 1000,
};
const panel: CSSProperties = {
  background: "#fff",
  padding: 20,
  borderRadius: 10,
  width: "min(900px, calc(100vw - 40px))",
  maxHeight: "calc(100vh - 40px)",
  overflow: "auto",
  boxShadow: "0 12px 40px rgba(0,0,0,0.3)",
  font: "14px system-ui, sans-serif",
};
const row: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  margin: "8px 0",
};
const colorGrid: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) 120px",
  alignItems: "end",
  gap: 10,
  margin: "6px 0 10px",
};
const compactRow: CSSProperties = {
  display: "grid",
  gap: 4,
  color: "#334",
  fontSize: 12,
};
const colorControls: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "44px minmax(0, 1fr)",
  gap: 8,
};
const previewFrame: CSSProperties = {
  position: "relative",
  margin: "10px 0",
  overflow: "hidden",
  border: "1px solid #cfd3da",
  background: "#f6f7f8",
  cursor: "crosshair",
};
const previewImage: CSSProperties = {
  display: "block",
  width: "100%",
  height: "auto",
  userSelect: "none",
};
const previewOverlay: CSSProperties = {
  position: "absolute",
  inset: 0,
  width: "100%",
  height: "100%",
  pointerEvents: "none",
};
const selectionStatus: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  marginTop: 6,
  color: "#556",
  fontSize: 12,
};
