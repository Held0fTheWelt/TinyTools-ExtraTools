import { useMemo } from "react";
import type { TrackShape } from "../model/shape";
import { sampleShape, polylineLength, boundingBox } from "../geometry/metrics";
import { resolveTrackLayouts } from "../model/layouts";

export function Metrics({ shape }: { shape: TrackShape }) {
  const layouts = useMemo(() => resolveTrackLayouts(shape), [shape]);
  const pts = useMemo(() => sampleShape(layouts[0].shape), [layouts]);
  const length = polylineLength(pts);
  const bb = boundingBox(pts);
  const extraLayouts = layouts.slice(1);

  return (
    <div data-testid="metrics">
      <span>Main Length: {length.toFixed(1)} m</span>
      {" | "}
      <span>Spline Points: {pts.length}</span>
      {" | "}
      <span>
        Bounding Box: {bb.w.toFixed(1)} m x {bb.h.toFixed(1)} m
      </span>
      {extraLayouts.length > 0 && (
        <>
          {" | "}
          <span>
            Layouts: {layouts.length} ({extraLayouts.map((layout) => layout.label).join(", ")})
          </span>
        </>
      )}
    </div>
  );
}

