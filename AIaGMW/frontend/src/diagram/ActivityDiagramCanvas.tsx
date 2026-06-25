import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type ActivityDiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function ActivityDiagramCanvas(props: ActivityDiagramCanvasProps) {
  return <BaseDiagramCanvas variant="activity" {...props} />;
}
