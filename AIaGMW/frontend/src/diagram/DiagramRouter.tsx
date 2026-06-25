import type { DiagramDetail, PatchPreviewResponse } from "@aiagmw/shared";
import { ActivityDiagramCanvas } from "./ActivityDiagramCanvas";
import { ComponentDiagramCanvas } from "./ComponentDiagramCanvas";
import { DeploymentDiagramCanvas } from "./DeploymentDiagramCanvas";
import { DiagramCanvas } from "./DiagramCanvas";
import { SequenceDiagramCanvas } from "./SequenceDiagramCanvas";
import { StateDiagramCanvas } from "./StateDiagramCanvas";

export interface DiagramRouterProps {
  detail: DiagramDetail | null;
  selectedElementId: string | null;
  selectedRelationId: string | null;
  diffPreview: PatchPreviewResponse | null;
  onSelectElement: (elementId: string | null) => void;
  onSelectRelation: (relationId: string | null) => void;
  onMoveNode: (elementId: string, x: number, y: number) => void;
  onResizeNode: (elementId: string, width: number, height: number) => void;
  onCreateRelation: (from: string, to: string) => void;
  onDeleteSelected?: () => void;
  onDuplicateSelected?: () => void;
}

export function DiagramRouter(props: DiagramRouterProps) {
  const diagramType = props.detail?.diagram.diagramType ?? "class";

  switch (diagramType) {
    case "component":
      return <ComponentDiagramCanvas {...props} />;
    case "sequence":
      return <SequenceDiagramCanvas {...props} />;
    case "state":
      return <StateDiagramCanvas {...props} />;
    case "activity":
      return <ActivityDiagramCanvas {...props} />;
    case "deployment":
      return <DeploymentDiagramCanvas {...props} />;
    case "class":
    case "package":
    case "mixed":
    default:
      return <DiagramCanvas {...props} />;
  }
}
