import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type DiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function DiagramCanvas(props: DiagramCanvasProps) {
  return <BaseDiagramCanvas variant="class" {...props} />;
}
