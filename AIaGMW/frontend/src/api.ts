import type {
  ApprovalRecord,
  DiagramDetail,
  DiagramSummary,
  DiagramType,
  ElementKind,
  ModelSummary,
  ModelType,
  PatchPreviewResponse,
  PatchProposal,
  ProposalSummary,
  RelationKind,
  UmlElement,
  UmlRelation,
  WorkspaceInfoResponse
} from "@aiagmw/shared";

export interface ImportDiagramPreviewResponse {
  proposal: PatchProposal;
  conflicts: unknown[];
  sourceRelativePath: string;
  imported: { elements: number; relations: number };
  preview: PatchPreviewResponse["diff"] | null;
  applicable: boolean;
}

const apiBase = import.meta.env.VITE_API_URL ?? "http://localhost:3000";

export async function getWorkspaceInfo(): Promise<WorkspaceInfoResponse> {
  return request("/api/workspace/info");
}

export async function openWorkspace(path: string): Promise<WorkspaceInfoResponse> {
  return request("/api/workspace/open", {
    method: "POST",
    body: JSON.stringify({ path })
  });
}

export async function createWorkspace(input: { path: string; id: string; name: string; description?: string }) {
  return request<WorkspaceInfoResponse>("/api/workspace/create", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function undoWorkspace(): Promise<WorkspaceInfoResponse> {
  return request("/api/history/undo", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function redoWorkspace(): Promise<WorkspaceInfoResponse> {
  return request("/api/history/redo", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function importDiagramPreview(body: {
  format: "plantuml" | "mermaid";
  source: string;
  name?: string;
  sourcePath?: string;
}) {
  return request<ImportDiagramPreviewResponse>("/api/import/diagram/preview", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function importDiagramAsProposal(body: {
  format: "plantuml" | "mermaid";
  source: string;
  name?: string;
  sourcePath?: string;
}) {
  return request<ImportDiagramPreviewResponse & { summary?: ProposalSummary }>("/api/import/diagram", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

/** @deprecated Use importDiagramAsProposal for proposal flow or importDiagramPreview for preview-only. */
export async function importDiagramSource(body: { format: "plantuml" | "mermaid"; source: string; name?: string; sourcePath?: string }) {
  return importDiagramAsProposal(body);
}

export async function autoLayoutDiagram(diagramId: string): Promise<DiagramDetail> {
  return request(`/api/diagrams/${encodeURIComponent(diagramId)}/auto-layout`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function getConnectorStatus() {
  return request<{
    enabled: boolean;
    connectors: unknown[];
    status: Record<string, unknown>;
    diagnostics: Array<{ level: string; code: string; message: string }>;
  }>("/api/connectors/status");
}

export async function akdbFetchContext(body: { task: string; projectId?: string }) {
  return request("/api/connectors/akdb/context", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function akdbListDiagrams(query?: { kind?: string; limit?: number; query?: string }) {
  const params = new URLSearchParams();
  if (query?.kind) {
    params.set("kind", query.kind);
  }
  if (query?.limit !== undefined) {
    params.set("limit", String(query.limit));
  }
  if (query?.query) {
    params.set("query", query.query);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/connectors/akdb/diagrams${suffix}`);
}

export async function akdbImportDiagram(body: { diagramId: string; name?: string; submit?: boolean }) {
  return request("/api/connectors/akdb/import", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function exportDiagramSource(diagramId: string, format: "plantuml" | "mermaid") {
  return request<{ format: "plantuml" | "mermaid"; diagramId: string; path: string; source: string }>(
    `/api/export/diagrams/${encodeURIComponent(diagramId)}`,
    {
      method: "POST",
      body: JSON.stringify({ format })
    }
  );
}

export async function getDiagram(diagramId: string): Promise<DiagramDetail> {
  return request(`/api/diagrams/${encodeURIComponent(diagramId)}`);
}

export async function getModels(): Promise<{ models: ModelSummary[] }> {
  return request("/api/workspace/models");
}

export async function createModel(body: { name: string; modelType: ModelType }) {
  return request<{ model: { id: string; name: string; modelType: ModelType } }>("/api/models", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getDiagrams(): Promise<{ diagrams: DiagramSummary[] }> {
  return request("/api/workspace/diagrams");
}

export async function createDiagram(body: { name: string; diagramType: DiagramType; modelRefs?: string[] }) {
  return request<{ diagram: { id: string; name: string; diagramType: DiagramType } }>("/api/diagrams", {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getProposals(): Promise<{ proposals: ProposalSummary[] }> {
  return request("/api/proposals");
}

export async function getProposal(proposalId: string): Promise<{ proposal: PatchProposal; path: string }> {
  return request(`/api/proposals/${encodeURIComponent(proposalId)}`);
}

export async function previewProposal(proposalId: string): Promise<PatchPreviewResponse> {
  return request(`/api/proposals/${encodeURIComponent(proposalId)}/preview`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function approveProposal(proposalId: string, approval: Omit<ApprovalRecord, "approvedAt">) {
  return request<{ proposal: ProposalSummary }>(`/api/proposals/${encodeURIComponent(proposalId)}/approve`, {
    method: "POST",
    body: JSON.stringify(approval)
  });
}

export async function applyProposal(proposalId: string, appliedBy = "user") {
  return request(`/api/proposals/${encodeURIComponent(proposalId)}/apply`, {
    method: "POST",
    body: JSON.stringify({ appliedBy })
  });
}

export async function rejectProposal(proposalId: string) {
  return request<{ proposal: ProposalSummary }>(`/api/proposals/${encodeURIComponent(proposalId)}/reject`, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function createElement(diagramId: string, body: { kind: ElementKind; name: string; x?: number; y?: number; width?: number; height?: number }) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/elements`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function addElementToDiagram(
  diagramId: string,
  body: { elementId: string; x?: number; y?: number; width?: number; height?: number }
) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/element-refs`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function createRelation(
  diagramId: string,
  body: { kind: RelationKind; from: string; to: string; name?: string }
) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/relations`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function addRelationToDiagram(
  diagramId: string,
  body: { relationId: string; x?: number; y?: number; width?: number; height?: number }
) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/relation-refs`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function removeElementFromDiagram(diagramId: string, elementId: string) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/elements/${encodeURIComponent(elementId)}`, {
    method: "DELETE"
  });
}

export async function updateRelation(modelId: string, relationId: string, updates: Partial<UmlRelation>) {
  return request<{ relation: UmlRelation }>(
    `/api/models/${encodeURIComponent(modelId)}/relations/${encodeURIComponent(relationId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates)
    }
  );
}

export async function removeRelationFromDiagram(diagramId: string, relationId: string) {
  return request<DiagramDetail>(`/api/diagrams/${encodeURIComponent(diagramId)}/relations/${encodeURIComponent(relationId)}`, {
    method: "DELETE"
  });
}

export async function deleteRelationFromModel(modelId: string, relationId: string) {
  return request<{ ok: true }>(`/api/models/${encodeURIComponent(modelId)}/relations/${encodeURIComponent(relationId)}`, {
    method: "DELETE"
  });
}

export async function deleteElementFromModel(modelId: string, elementId: string) {
  return request<{ ok: true }>(`/api/models/${encodeURIComponent(modelId)}/elements/${encodeURIComponent(elementId)}`, {
    method: "DELETE"
  });
}

export async function updateNodeLayout(
  diagramId: string,
  elementId: string,
  updates: { x?: number; y?: number; width?: number; height?: number }
) {
  return request(`/api/diagrams/${encodeURIComponent(diagramId)}/layout/nodes/${encodeURIComponent(elementId)}`, {
    method: "POST",
    body: JSON.stringify(updates)
  });
}

export async function updateNodePosition(diagramId: string, elementId: string, x: number, y: number) {
  return updateNodeLayout(diagramId, elementId, { x, y });
}

export async function updateElement(modelId: string, elementId: string, updates: Partial<UmlElement>) {
  return request<{ element: UmlElement }>(
    `/api/models/${encodeURIComponent(modelId)}/elements/${encodeURIComponent(elementId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates)
    }
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}
