import { Box, FileJson, GitPullRequestDraft, Network, Plus } from "lucide-react";
import type { WorkspaceInfoResponse } from "@aiagmw/shared";

interface WorkspaceExplorerProps {
  info: WorkspaceInfoResponse | null;
  selectedDiagramId: string | null;
  onSelectDiagram: (diagramId: string) => void;
  onCreateModel: () => void;
  onCreateDiagram: () => void;
  canCreateDiagram: boolean;
}

export function WorkspaceExplorer({
  info,
  selectedDiagramId,
  onSelectDiagram,
  onCreateModel,
  onCreateDiagram,
  canCreateDiagram
}: WorkspaceExplorerProps) {
  if (!info?.workspace) {
    return <div className="explorer-empty">Workspace not loaded.</div>;
  }

  return (
    <div className="explorer">
      <div className="workspace-meta">
        <strong>{info.workspace.name}</strong>
        <span>{info.workspace.id}</span>
      </div>

      <section>
        <div className="section-heading">
          <h2>
            <FileJson size={15} aria-hidden />
            Models
          </h2>
          <button type="button" className="mini-action" title="Create model" onClick={onCreateModel}>
            <Plus size={14} aria-hidden />
          </button>
        </div>
        {info.index.models.map((model) => (
          <div key={model.id} className="explorer-row">
            <Box size={14} aria-hidden />
            <div>
              <strong>{model.name}</strong>
              <span>{model.elementCount} elements, {model.relationCount} relations</span>
            </div>
          </div>
        ))}
      </section>

      <section>
        <div className="section-heading">
          <h2>
            <Network size={15} aria-hidden />
            Diagrams
          </h2>
          <button
            type="button"
            className="mini-action"
            title="Create diagram"
            onClick={onCreateDiagram}
            disabled={!canCreateDiagram}
          >
            <Plus size={14} aria-hidden />
          </button>
        </div>
        {info.index.diagrams.map((diagram) => (
          <button
            key={diagram.id}
            type="button"
            className={diagram.id === selectedDiagramId ? "explorer-row active" : "explorer-row"}
            onClick={() => onSelectDiagram(diagram.id)}
          >
            <Network size={14} aria-hidden />
            <div>
              <strong>{diagram.name}</strong>
              <span>{diagram.diagramType} - {diagram.elementCount} elements</span>
            </div>
          </button>
        ))}
      </section>

      <section>
        <h2>
          <GitPullRequestDraft size={15} aria-hidden />
          Proposals
        </h2>
        {info.index.proposals.map((proposal) => (
          <div key={proposal.id} className="explorer-row">
            <GitPullRequestDraft size={14} aria-hidden />
            <div>
              <strong>{proposal.title}</strong>
              <span>{proposal.status} - {proposal.operationCount} ops</span>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
