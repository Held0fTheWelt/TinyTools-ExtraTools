import { BaseDiagramCanvas, type BaseDiagramCanvasProps } from "./BaseDiagramCanvas";

export type DeploymentDiagramCanvasProps = Omit<BaseDiagramCanvasProps, "variant">;

export function DeploymentDiagramCanvas(props: DeploymentDiagramCanvasProps) {
  return <BaseDiagramCanvas variant="deployment" {...props} />;
}
