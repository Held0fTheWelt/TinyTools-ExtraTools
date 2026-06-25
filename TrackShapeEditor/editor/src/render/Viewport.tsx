import { useMemo, useRef, useCallback } from "react";
import type { TrackShape } from "../model/shape";
import { sampleShape, boundingBox, polylineLength } from "../geometry/metrics";
import { meshBoundaries } from "../validation/mesh";
import { scalePreview } from "../validation/scale";
import { type View } from "./coords";
import { usePointerDrag } from "../hooks/usePointerDrag";
import type { ReferenceImageLayer } from "../io/referenceImage";
import { resolveTrackLayouts } from "../model/layouts";

export interface ViewportProps {
  shape: TrackShape;
  focusId?: string | null;
  showMeshTicks?: boolean;
  pieceLengthM?: number;
  showScalePreview?: boolean;
  referenceImage?: ReferenceImageLayer | null;
  onAnchorDrag?: (id: string, w: { x: number; y: number }, mirror: boolean) => void;
  onHandleDrag?: (segId: string, end: "from" | "to", w: { x: number; y: number }, mirror: boolean) => void;
  onSelectAnchor?: (id: string) => void;
  onSelectSegment?: (id: string) => void;
}

export function Viewport({
  shape,
  focusId,
  showMeshTicks,
  pieceLengthM = 20,
  showScalePreview,
  referenceImage,
  onAnchorDrag,
  onHandleDrag,
  onSelectAnchor,
  onSelectSegment,
}: ViewportProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const layouts = useMemo(() => resolveTrackLayouts(shape), [shape]);
  const pts = useMemo(() => sampleShape(shape), [shape]);
  const allPts = useMemo(() => layouts.flatMap((layout) => sampleShape(layout.shape)), [layouts]);
  const bb = useMemo(() => boundingBox(allPts.length ? allPts : pts), [allPts, pts]);
  const viewportBounds = useMemo(() => {
    const maxX = bb.minX + bb.w;
    const maxY = bb.minY + bb.h;
    if (!referenceImage?.visible) return bb;
    const refMaxX = referenceImage.x + referenceImage.width;
    const refMaxY = referenceImage.y + referenceImage.height;
    const minX = Math.min(bb.minX, referenceImage.x);
    const minY = Math.min(bb.minY, referenceImage.y);
    return {
      minX,
      minY,
      w: Math.max(maxX, refMaxX) - minX,
      h: Math.max(maxY, refMaxY) - minY,
    };
  }, [bb, referenceImage]);
  const pad = 40;
  const vbMinX = viewportBounds.minX - pad;
  const vbMinY = viewportBounds.minY - pad;
  const vbW = viewportBounds.w + 2 * pad;
  const vbH = viewportBounds.h + 2 * pad;
  const vb = `${vbMinX} ${vbMinY} ${vbW} ${vbH}`;

  const makeView = useCallback(
    (): View => ({
      vbMinX,
      vbMinY,
      vbW,
      vbH,
      pxW: svgRef.current?.clientWidth ?? 800,
      pxH: svgRef.current?.clientHeight ?? 600,
      flipY: true,
    }),
    [vbMinX, vbMinY, vbW, vbH],
  );

  const poly = pts.map((p) => `${p.x},${p.y}`).join(" ");
  const meshTicks = showMeshTicks ? meshBoundaries(pts, pieceLengthM) : [];
  const rawLen = polylineLength(pts);
  const targetM = shape.units.target_length_m ?? rawLen;
  const scale = showScalePreview ? scalePreview(rawLen, targetM) : null;

  const activeAnchor = useRef<string | null>(null);
  const activeHandle = useRef<{ segId: string; end: "from" | "to" } | null>(null);

  const anchorDrag = usePointerDrag(svgRef, (w, _mirror) => {
    if (activeAnchor.current) onAnchorDrag?.(activeAnchor.current, w, true);
  });
  const handleDrag = usePointerDrag(svgRef, (w, mirror) => {
    if (activeHandle.current) onHandleDrag?.(activeHandle.current.segId, activeHandle.current.end, w, mirror);
  });

  return (
    <svg
      ref={svgRef}
      data-testid="viewport"
      viewBox={vb}
      width="100%"
      height="100%"
      style={{ transform: "scaleY(-1)", background: "#f8f8f8" }}
      onPointerMove={(e) => {
        anchorDrag.onMoveEvt(e, makeView());
        handleDrag.onMoveEvt(e, makeView());
      }}
      onPointerUp={() => {
        anchorDrag.onUp();
        handleDrag.onUp();
        activeAnchor.current = null;
        activeHandle.current = null;
      }}
    >
      {referenceImage?.visible && (
        <g data-reference-image opacity={referenceImage.opacity} pointerEvents="none">
          <image
            href={referenceImage.href}
            x={referenceImage.x}
            y={-(referenceImage.y + referenceImage.height)}
            width={referenceImage.width}
            height={referenceImage.height}
            preserveAspectRatio="none"
            transform="scale(1 -1)"
          />
        </g>
      )}

      {layouts
        .filter((layout) => !layout.isMain)
        .map((layout) => (
          <polyline
            key={layout.id}
            data-layout-preview={layout.id}
            points={sampleShape(layout.shape)
              .map((p) => `${p.x},${p.y}`)
              .join(" ")}
            fill="none"
            stroke={layout.kind === "pit_lane" ? "#d95f02" : "#7570b3"}
            strokeWidth={3}
            strokeDasharray={layout.kind === "pit_lane" ? "12 5" : "7 5"}
          />
        ))}

      <polyline data-preview points={poly} fill="none" stroke="#1b9e77" strokeWidth={4} />

      {shape.segments.map((s) => {
        const from = shape.anchors.find((a) => a.id === s.from)!;
        const to = shape.anchors.find((a) => a.id === s.to)!;
        const focused = focusId === s.id;
        if (s.type === "line") {
          return (
            <line
              key={s.id}
              data-segment={s.id}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={focused ? "#e7298a" : "#666"}
              strokeWidth={focused ? 6 : 2}
              strokeDasharray={focused ? "8 4" : undefined}
              onClick={() => onSelectSegment?.(s.id)}
            />
          );
        }
        const d = `M ${from.x} ${from.y} C ${s.handle_from.x} ${s.handle_from.y} ${s.handle_to.x} ${s.handle_to.y} ${to.x} ${to.y}`;
        return (
          <g key={s.id}>
            <path
              data-segment={s.id}
              d={d}
              fill="none"
              stroke={focused ? "#e7298a" : "#999"}
              strokeWidth={focused ? 4 : 1}
              strokeDasharray={focused ? "8 4" : undefined}
              onClick={() => onSelectSegment?.(s.id)}
            />
            <line x1={from.x} y1={from.y} x2={s.handle_from.x} y2={s.handle_from.y} stroke="#aaa" strokeWidth={1} />
            <line x1={to.x} y1={to.y} x2={s.handle_to.x} y2={s.handle_to.y} stroke="#aaa" strokeWidth={1} />
            <circle
              data-handle={`${s.id}-from`}
              cx={s.handle_from.x}
              cy={s.handle_from.y}
              r={6}
              fill="#7570b3"
              style={{ cursor: "pointer" }}
              onPointerDown={(e) => {
                activeHandle.current = { segId: s.id, end: "from" };
                handleDrag.onDown(e, makeView());
              }}
            />
            <circle
              data-handle={`${s.id}-to`}
              cx={s.handle_to.x}
              cy={s.handle_to.y}
              r={6}
              fill="#7570b3"
              style={{ cursor: "pointer" }}
              onPointerDown={(e) => {
                activeHandle.current = { segId: s.id, end: "to" };
                handleDrag.onDown(e, makeView());
              }}
            />
          </g>
        );
      })}

      {meshTicks.map((p, i) => (
        <g key={i} data-mesh-tick transform={`translate(${p.x},${p.y})`}>
          <line x1={-4} y1={0} x2={4} y2={0} stroke="#d95f02" strokeWidth={2} />
          <line x1={0} y1={-4} x2={0} y2={4} stroke="#d95f02" strokeWidth={2} />
        </g>
      ))}

      {scale && (
        <text x={vbMinX + 10} y={vbMinY + vbH - 10} fontSize={14} fill="#333">
          Scale: {scale.factor.toFixed(4)} {scale.warn ? "(warn)" : ""}
        </text>
      )}

      {shape.anchors.map((a) => {
        const focused = focusId === a.id;
        return (
          <circle
            key={a.id}
            data-anchor={a.id}
            cx={a.x}
            cy={a.y}
            r={focused ? 12 : 8}
            fill={focused ? "#e7298a" : "#222"}
            stroke={focused ? "#fff" : undefined}
            strokeWidth={focused ? 2 : 0}
            style={{ cursor: onAnchorDrag ? "grab" : "pointer" }}
            onClick={() => onSelectAnchor?.(a.id)}
            onPointerDown={(e) => {
              if (!onAnchorDrag) return;
              activeAnchor.current = a.id;
              anchorDrag.onDown(e, makeView());
            }}
          />
        );
      })}
    </svg>
  );
}
