import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type ComponentDiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function ComponentDiagramCanvas(props: ComponentDiagramCanvasProps) {
  return <BaseDiagramCanvas variant="component" {...props} />;
}
