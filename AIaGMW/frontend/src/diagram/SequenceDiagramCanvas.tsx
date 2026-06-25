import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type SequenceDiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function SequenceDiagramCanvas(props: SequenceDiagramCanvasProps) {
  return <BaseDiagramCanvas variant="sequence" {...props} />;
}
