export type DiagnosticLevel = "error" | "warning" | "info" | "suggestion";

export interface Diagnostic {
  level: DiagnosticLevel;
  code: string;
  message: string;
  file?: string;
  targetId?: string;
  category?: string;
}

export interface WorkspaceManifest {
  schema: "umlworkspace.v1";
  id: string;
  name: string;
  description?: string;
  paths: {
    models: string;
    diagrams: string;
    layouts: string;
    proposals: string;
    history: string;
    imports?: string;
    exports?: string;
    docs?: string;
  };
  features?: Record<string, boolean>;
  metadata?: Record<string, unknown>;
}

export type ModelType =
  | "class-model"
  | "component-model"
  | "package-model"
  | "sequence-model"
  | "state-model"
  | "activity-model"
  | "deployment-model"
  | "mixed-model";

export type ElementKind =
  | "class"
  | "abstract_class"
  | "interface"
  | "enum"
  | "component"
  | "package"
  | "layer"
  | "module"
  | "service"
  | "subsystem"
  | "actor"
  | "node"
  | "artifact"
  | "note"
  | "boundary"
  | "lifeline"
  | "activation"
  | "fragment"
  | "state_node"
  | "pseudostate"
  | "final_state"
  | "action"
  | "decision"
  | "merge"
  | "fork"
  | "join"
  | "deployment_spec";

export type RelationKind =
  | "association"
  | "dependency"
  | "inheritance"
  | "implementation"
  | "composition"
  | "aggregation"
  | "realization"
  | "containment"
  | "uses"
  | "creates"
  | "owns"
  | "publishes"
  | "subscribes"
  | "calls"
  | "sync_message"
  | "async_message"
  | "reply"
  | "destroy"
  | "transition"
  | "control_flow"
  | "object_flow"
  | "deploy"
  | "communicate";

export interface UmlProperty {
  name: string;
  type?: string;
  visibility?: string;
  multiplicity?: string;
  [key: string]: unknown;
}

export interface UmlParameter {
  name: string;
  type?: string;
}

export interface UmlMethod {
  name: string;
  returnType?: string;
  visibility?: string;
  parameters?: UmlParameter[];
  [key: string]: unknown;
}

export interface UmlElement {
  id: string;
  kind: ElementKind;
  name: string;
  stereotypes?: string[];
  visibility?: string;
  abstract?: boolean;
  responsibilities?: string[];
  properties?: UmlProperty[];
  methods?: UmlMethod[];
  constraints?: string[];
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface UmlRelation {
  id: string;
  kind: RelationKind;
  from: string;
  to: string;
  name?: string;
  fromMultiplicity?: string;
  toMultiplicity?: string;
  navigability?: string;
  stereotypes?: string[];
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface UmlModel {
  schema: "umlmodel.v1";
  id: string;
  name: string;
  modelType: ModelType;
  elements: UmlElement[];
  relations: UmlRelation[];
  metadata?: Record<string, unknown>;
}

export type DiagramType =
  | "class"
  | "component"
  | "package"
  | "sequence"
  | "state"
  | "activity"
  | "deployment"
  | "mixed";

export interface UmlDiagram {
  schema: "umldiagram.v1";
  id: string;
  name: string;
  diagramType: DiagramType;
  modelRefs: string[];
  elementRefs: string[];
  relationRefs: string[];
  metadata?: Record<string, unknown>;
}

export interface LayoutPoint {
  x: number;
  y: number;
}

export interface NodeLayout {
  x: number;
  y: number;
  width?: number;
  height?: number;
  collapsed?: boolean;
  locked?: boolean;
}

export interface EdgeLayout {
  points?: LayoutPoint[];
}

export interface UmlLayout {
  schema: "umllayout.v1";
  diagramId: string;
  nodes: Record<string, NodeLayout>;
  edges: Record<string, EdgeLayout>;
}

export type PatchStatus = "draft" | "pending" | "accepted" | "rejected" | "archived";
export type PatchRisk = "low" | "medium" | "high";

export interface PatchOperation {
  op: string;
  modelId?: string;
  diagramId?: string;
  elementId?: string;
  relationId?: string;
  element?: Partial<UmlElement>;
  relation?: Partial<UmlRelation>;
  updates?: Record<string, unknown>;
  reason?: string;
}

export interface PatchProposal {
  schema: "umlpatch.v1";
  id: string;
  title: string;
  intent: string;
  author?: Record<string, unknown>;
  status: PatchStatus;
  risk?: PatchRisk;
  reasoningSummary?: string;
  operations: PatchOperation[];
  metadata?: Record<string, unknown>;
}

export interface ModelSummary {
  id: string;
  name: string;
  modelType: ModelType;
  path: string;
  elementCount: number;
  relationCount: number;
  tags: string[];
}

export interface DiagramSummary {
  id: string;
  name: string;
  diagramType: DiagramType;
  path: string;
  modelRefs: string[];
  elementCount: number;
  relationCount: number;
  tags: string[];
}

export interface ProposalSummary {
  id: string;
  title: string;
  status: PatchStatus;
  risk?: PatchRisk;
  path: string;
  operationCount: number;
}

export interface WorkspaceIndex {
  models: ModelSummary[];
  diagrams: DiagramSummary[];
  proposals: ProposalSummary[];
  elementToModel: Record<string, string>;
  elementToDiagrams: Record<string, string[]>;
  relationToModel: Record<string, string>;
  tags: Record<string, string[]>;
}

export interface DiagramDetail {
  diagram: UmlDiagram;
  layout: UmlLayout;
  models: UmlModel[];
  elements: Array<UmlElement & { modelId: string }>;
  relations: Array<UmlRelation & { modelId: string }>;
  diagnostics: Diagnostic[];
}

export interface WorkspaceInfoResponse {
  workspace: WorkspaceManifest | null;
  index: WorkspaceIndex;
  diagnostics: Diagnostic[];
  root: string;
  history?: WorkspaceHistoryStatus;
  revision?: number;
  externalChangeAt?: string | null;
}

export interface PatchDiffSummary {
  addedElements: Array<{ modelId: string; element: UmlElement }>;
  removedElements: Array<{ modelId: string; element: UmlElement }>;
  updatedElements: Array<{ modelId: string; elementId: string; before: UmlElement; after: UmlElement }>;
  addedRelations: Array<{ modelId: string; relation: UmlRelation }>;
  removedRelations: Array<{ modelId: string; relation: UmlRelation }>;
  updatedRelations: Array<{ modelId: string; relationId: string; before: UmlRelation; after: UmlRelation }>;
  addedDiagrams: UmlDiagram[];
  updatedDiagrams: Array<{ diagramId: string; before: UmlDiagram; after: UmlDiagram }>;
  layoutChanges: Array<{ diagramId: string; elementId: string; before?: Record<string, unknown>; after?: Record<string, unknown> }>;
  affectedModelIds: string[];
  affectedDiagramIds: string[];
}

export interface PatchPreviewResponse {
  proposal: PatchProposal;
  applicable: boolean;
  diagnostics: Diagnostic[];
  diff: PatchDiffSummary;
  operationErrors: Array<{ op: string; message: string }>;
}

export interface ApprovalRecord {
  approvedBy: string;
  approvedAt: string;
  approvalNote?: string;
  validationStatus?: string;
}

export interface WorkspaceHistoryStatus {
  undoCount: number;
  redoCount: number;
  nextUndoLabel?: string;
  nextRedoLabel?: string;
}
