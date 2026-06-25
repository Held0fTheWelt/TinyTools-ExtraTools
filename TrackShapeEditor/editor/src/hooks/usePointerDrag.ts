import { useRef, useCallback } from "react";
import { screenToWorld, type View } from "../render/coords";

export function usePointerDrag(
  vRef: React.RefObject<SVGSVGElement | null>,
  onMove: (w: { x: number; y: number }, mirror: boolean) => void,
) {
  const active = useRef(false);

  const onDown = useCallback(
    (e: React.PointerEvent, view: View) => {
      (e.target as Element).setPointerCapture(e.pointerId);
      active.current = true;
      const rect = vRef.current!.getBoundingClientRect();
      const w = screenToWorld(e.clientX - rect.left, e.clientY - rect.top, view);
      onMove(w, !e.altKey);
    },
    [onMove, vRef],
  );

  const onMoveEvt = useCallback(
    (e: React.PointerEvent, view: View) => {
      if (!active.current) return;
      const rect = vRef.current!.getBoundingClientRect();
      onMove(screenToWorld(e.clientX - rect.left, e.clientY - rect.top, view), !e.altKey);
    },
    [onMove, vRef],
  );

  const onUp = useCallback(() => {
    active.current = false;
  }, []);

  return { onDown, onMoveEvt, onUp };
}
