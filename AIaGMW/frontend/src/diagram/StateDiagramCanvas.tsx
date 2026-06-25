import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type StateDiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function StateDiagramCanvas(props: StateDiagramCanvasProps) {
  return <BaseDiagramCanvas variant="state" {...props} />;
}
