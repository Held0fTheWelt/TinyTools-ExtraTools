import {
  Activity,
  Bot,
  Boxes,
  CheckCircle2,
  CircleAlert,
  Download,
  FolderOpen,
  Grid3x3,
  Plus,
  Redo2,
  RefreshCw,
  Save,
  Undo2,
  Upload,
  X
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  DiagramDetail,
  DiagramType,
  Diagnostic,
  ElementKind,
  ModelType,
  PatchPreviewResponse,
  RelationKind,
  UmlElement,
  WorkspaceInfoResponse
} from "@aiagmw/shared";
import type { ImportDiagramPreviewResponse } from "./api";
import {
  addElementToDiagram,
  addRelationToDiagram,
  autoLayoutDiagram,
  createDiagram,
  createElement,
  createModel,
  createRelation,
  createWorkspace,
  deleteElementFromModel,
  deleteRelationFromModel,
  exportDiagramSource,
  getDiagram,
  getWorkspaceInfo,
  importDiagramAsProposal,
  importDiagramPreview,
  openWorkspace,
  removeElementFromDiagram,
  removeRelationFromDiagram,
  redoWorkspace,
  undoWorkspace,
  updateElement,
  updateNodeLayout,
  updateRelation,
  updateNodePosition
} from "./api";
import { DiagramRouter } from "./diagram/DiagramRouter";
import { getPaletteForDiagramType } from "./diagram/palettes";
import { Inspector } from "./components/Inspector";
import { DiagnosticsPanel } from "./validation/DiagnosticsPanel";
import { WorkspaceExplorer } from "./explorer/WorkspaceExplorer";
import { ProposalReviewPanel } from "./proposals/ProposalReviewPanel";


const diagramTypes: DiagramType[] = ["class", "component", "package", "sequence", "state", "activity", "deployment", "mixed"];
const modelTypes: ModelType[] = [
  "class-model",
  "component-model",
  "package-model",
  "sequence-model",
  "state-model",
  "activity-model",
  "deployment-model",
  "mixed-model"
];

export function App() {
  const [workspaceInfo, setWorkspaceInfo] = useState<WorkspaceInfoResponse | null>(null);
  const [selectedDiagramId, setSelectedDiagramId] = useState<string | null>(null);
  const [diagram, setDiagram] = useState<DiagramDetail | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [selectedRelationId, setSelectedRelationId] = useState<string | null>(null);
  const [selectedRelationKind, setSelectedRelationKind] = useState<RelationKind>("association");
  const [createModelOpen, setCreateModelOpen] = useState(false);
  const [createDiagramOpen, setCreateDiagramOpen] = useState(false);
  const [addExistingElementOpen, setAddExistingElementOpen] = useState(false);
  const [addExistingRelationOpen, setAddExistingRelationOpen] = useState(false);
  const [createWorkspaceOpen, setCreateWorkspaceOpen] = useState(false);
  const [openWorkspaceOpen, setOpenWorkspaceOpen] = useState(false);
  const [importDiagramOpen, setImportDiagramOpen] = useState(false);
  const [exportDiagramOpen, setExportDiagramOpen] = useState(false);
  const [exportResult, setExportResult] = useState<{ format: "plantuml" | "mermaid"; path: string; source: string } | null>(null);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [diffPreview, setDiffPreview] = useState<PatchPreviewResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRevision, setLastRevision] = useState<number | null>(null);

  const loadWorkspace = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const info = await getWorkspaceInfo();
      setWorkspaceInfo(info);
      setLastRevision(info.revision ?? null);
      const nextDiagramId = selectedDiagramId ?? info.index.diagrams[0]?.id ?? null;
      setSelectedDiagramId(nextDiagramId);
      if (nextDiagramId) {
        setDiagram(await getDiagram(nextDiagramId));
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load workspace.");
    } finally {
      setBusy(false);
    }
  }, [selectedDiagramId]);

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    const interval = window.setInterval(async () => {
      try {
        const info = await getWorkspaceInfo();
        if (lastRevision !== null && info.revision !== undefined && info.revision !== lastRevision) {
          setWorkspaceInfo(info);
          if (selectedDiagramId) {
            setDiagram(await getDiagram(selectedDiagramId));
          }
        }
        setLastRevision(info.revision ?? null);
      } catch {
        // ignore polling errors
      }
    }, 4000);
    return () => window.clearInterval(interval);
  }, [lastRevision, selectedDiagramId]);

  useEffect(() => {
    if (!selectedDiagramId) {
      setDiagram(null);
      return;
    }

    let cancelled = false;
    setBusy(true);
    getDiagram(selectedDiagramId)
      .then((nextDiagram) => {
        if (!cancelled) {
          setDiagram(nextDiagram);
          setSelectedElementId(null);
          setSelectedRelationId(null);
        }
      })
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Could not load diagram."))
      .finally(() => setBusy(false));

    return () => {
      cancelled = true;
    };
  }, [selectedDiagramId]);

  const selectedElement = useMemo(
    () => diagram?.elements.find((element) => element.id === selectedElementId) ?? null,
    [diagram, selectedElementId]
  );
  const selectedRelation = useMemo(
    () => diagram?.relations.find((relation) => relation.id === selectedRelationId) ?? null,
    [diagram, selectedRelationId]
  );
  const existingElementOptions = useMemo(() => {
    if (!diagram) {
      return [];
    }

    const visibleElementIds = new Set(diagram.elements.map((element) => element.id));
    return diagram.models.flatMap((model) =>
      model.elements
        .filter((element) => !visibleElementIds.has(element.id))
        .map((element) => ({
          id: element.id,
          name: element.name,
          kind: element.kind,
          modelName: model.name
        }))
    );
  }, [diagram]);
  const existingRelationOptions = useMemo(() => {
    if (!diagram) {
      return [];
    }

    const visibleRelationIds = new Set(diagram.relations.map((relation) => relation.id));
    const elementNames = new Map(diagram.models.flatMap((model) => model.elements.map((element) => [element.id, element.name] as const)));
    return diagram.models.flatMap((model) =>
      model.relations
        .filter((relation) => !visibleRelationIds.has(relation.id))
        .map((relation) => ({
          id: relation.id,
          name: relation.name ?? relation.kind,
          kind: relation.kind,
          from: relation.from,
          to: relation.to,
          fromName: elementNames.get(endpointId(relation.from)) ?? endpointId(relation.from),
          toName: elementNames.get(endpointId(relation.to)) ?? endpointId(relation.to),
          modelName: model.name
        }))
    );
  }, [diagram]);

  const diagnostics: Diagnostic[] = useMemo(() => {
    const items = [...(workspaceInfo?.diagnostics ?? [])];
    if (error) {
      items.unshift({ level: "error", code: "ui.request_failed", message: error, category: "ui" });
    }
    return items;
  }, [workspaceInfo, error]);

  const palette = useMemo(
    () => getPaletteForDiagramType(diagram?.diagram.diagramType ?? "class"),
    [diagram?.diagram.diagramType]
  );

  useEffect(() => {
    if (!palette.relationKinds.includes(selectedRelationKind)) {
      setSelectedRelationKind(palette.relationKinds[0] ?? "association");
    }
  }, [palette, selectedRelationKind]);

  const duplicateSelectedElement = useCallback(async () => {
    if (!selectedElementId || !selectedDiagramId || !diagram) {
      return;
    }

    const element = diagram.elements.find((item) => item.id === selectedElementId);
    if (!element) {
      return;
    }

    const layout = diagram.layout.nodes[element.id];
    setBusy(true);
    try {
      let nextDiagram = await createElement(selectedDiagramId, {
        kind: element.kind,
        name: `${element.name} Copy`,
        x: (layout?.x ?? 180) + 48,
        y: (layout?.y ?? 180) + 48,
        width: layout?.width,
        height: layout?.height
      });
      const created = nextDiagram.elements.find((item) => item.name === `${element.name} Copy`);
      if (created) {
        await updateElement(created.modelId, created.id, {
          abstract: element.abstract,
          visibility: element.visibility,
          stereotypes: element.stereotypes,
          responsibilities: element.responsibilities,
          properties: element.properties,
          methods: element.methods,
          constraints: element.constraints,
          tags: element.tags,
          metadata: element.metadata
        });
        nextDiagram = await getDiagram(selectedDiagramId);
        setSelectedElementId(created.id);
        setSelectedRelationId(null);
      }
      setDiagram(nextDiagram);
      await loadWorkspace();
    } catch (duplicateError) {
      setError(duplicateError instanceof Error ? duplicateError.message : "Could not duplicate element.");
    } finally {
      setBusy(false);
    }
  }, [selectedElementId, selectedDiagramId, diagram, loadWorkspace]);

  async function addElement(kind: ElementKind) {
    if (!selectedDiagramId) {
      return;
    }

    const defaultName = kind === "interface" ? "INewPort" : `New ${kind.replaceAll("_", " ")}`;
    const name = window.prompt("Element name", defaultName);
    if (!name?.trim()) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await createElement(selectedDiagramId, {
        kind,
        name: name.trim(),
        x: 180 + (diagram?.elements.length ?? 0) * 32,
        y: 180 + (diagram?.elements.length ?? 0) * 24
      });
      setDiagram(nextDiagram);
      await loadWorkspace();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create element.");
    } finally {
      setBusy(false);
    }
  }

  function openAddExistingElementDialog() {
    if (!selectedDiagramId) {
      return;
    }
    if (!existingElementOptions.length) {
      setError("No hidden elements are available for this diagram.");
      return;
    }
    setAddExistingElementOpen(true);
  }

  async function addExistingElement(elementId: string) {
    if (!selectedDiagramId) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await addElementToDiagram(selectedDiagramId, {
        elementId,
        x: 180 + (diagram?.elements.length ?? 0) * 32,
        y: 180 + (diagram?.elements.length ?? 0) * 24
      });
      setDiagram(nextDiagram);
      setSelectedElementId(elementId);
      setSelectedRelationId(null);
      setAddExistingElementOpen(false);
      await loadWorkspace();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Could not add element to diagram.");
    } finally {
      setBusy(false);
    }
  }

  function openAddExistingRelationDialog() {
    if (!selectedDiagramId) {
      return;
    }
    if (!existingRelationOptions.length) {
      setError("No hidden relations are available for this diagram.");
      return;
    }
    setAddExistingRelationOpen(true);
  }

  async function addExistingRelation(relationId: string) {
    if (!selectedDiagramId) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await addRelationToDiagram(selectedDiagramId, {
        relationId,
        x: 180 + (diagram?.elements.length ?? 0) * 32,
        y: 180 + (diagram?.elements.length ?? 0) * 24
      });
      setDiagram(nextDiagram);
      setSelectedElementId(null);
      setSelectedRelationId(relationId);
      setAddExistingRelationOpen(false);
      await loadWorkspace();
    } catch (addError) {
      setError(addError instanceof Error ? addError.message : "Could not add relation to diagram.");
    } finally {
      setBusy(false);
    }
  }

  function openCreateDiagramDialog() {
    if (!workspaceInfo?.index.models.length) {
      setError("Create a model before creating a diagram.");
      return;
    }
    setCreateDiagramOpen(true);
  }

  async function addDiagram(input: { name: string; diagramType: DiagramType; modelId: string }) {
    setBusy(true);
    try {
      const created = await createDiagram({
        name: input.name.trim(),
        diagramType: input.diagramType,
        modelRefs: [input.modelId]
      });
      const info = await getWorkspaceInfo();
      setWorkspaceInfo(info);
      setSelectedDiagramId(created.diagram.id);
      setDiagram(await getDiagram(created.diagram.id));
      setSelectedElementId(null);
      setSelectedRelationId(null);
      setCreateDiagramOpen(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create diagram.");
    } finally {
      setBusy(false);
    }
  }

  async function addModel(input: { name: string; modelType: ModelType }) {
    setBusy(true);
    try {
      await createModel({
        name: input.name.trim(),
        modelType: input.modelType
      });
      setWorkspaceInfo(await getWorkspaceInfo());
      setCreateModelOpen(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create model.");
    } finally {
      setBusy(false);
    }
  }

  async function saveElement(modelId: string, elementId: string, updates: Partial<UmlElement>) {
    setBusy(true);
    try {
      await updateElement(modelId, elementId, updates);
      if (selectedDiagramId) {
        setDiagram(await getDiagram(selectedDiagramId));
      }
      await loadWorkspace();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save element.");
    } finally {
      setBusy(false);
    }
  }

  async function addRelation(from: string, to: string) {
    if (!selectedDiagramId || from === to) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await createRelation(selectedDiagramId, {
        kind: selectedRelationKind,
        from,
        to
      });
      setDiagram(nextDiagram);
      setSelectedElementId(null);
      const latestRelation = nextDiagram.relations.at(-1);
      setSelectedRelationId(latestRelation?.id ?? null);
      await loadWorkspace();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Could not create relation.");
    } finally {
      setBusy(false);
    }
  }

  async function removeSelectedFromDiagram(modelId: string, elementId: string) {
    if (!selectedDiagramId) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await removeElementFromDiagram(selectedDiagramId, elementId);
      setDiagram(nextDiagram);
      setSelectedElementId(null);
      await loadWorkspace();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Could not remove element from diagram.");
    } finally {
      setBusy(false);
    }
  }

  async function saveRelation(modelId: string, relationId: string, updates: Parameters<typeof updateRelation>[2]) {
    setBusy(true);
    try {
      await updateRelation(modelId, relationId, updates);
      if (selectedDiagramId) {
        setDiagram(await getDiagram(selectedDiagramId));
      }
      await loadWorkspace();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save relation.");
    } finally {
      setBusy(false);
    }
  }

  async function removeRelationSelectedFromDiagram(modelId: string, relationId: string) {
    if (!selectedDiagramId) {
      return;
    }

    setBusy(true);
    try {
      const nextDiagram = await removeRelationFromDiagram(selectedDiagramId, relationId);
      setDiagram(nextDiagram);
      setSelectedRelationId(null);
      await loadWorkspace();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Could not remove relation from diagram.");
    } finally {
      setBusy(false);
    }
  }

  function deleteSelectedFromCanvas() {
    if (selectedElementId && selectedDiagramId && diagram) {
      const element = diagram.elements.find((item) => item.id === selectedElementId);
      if (element) {
        void removeSelectedFromDiagram(element.modelId, element.id);
      }
      return;
    }
    if (selectedRelationId && selectedDiagramId && diagram) {
      const relation = diagram.relations.find((item) => item.id === selectedRelationId);
      if (relation) {
        void removeRelationSelectedFromDiagram(relation.modelId, relation.id);
      }
    }
  }

  function navigateDiagnostic(targetId: string) {
    const index = workspaceInfo?.index;
    if (!index) {
      return;
    }

    const diagramId =
      index.elementToDiagrams[targetId]?.[0] ??
      index.diagrams.find((entry) => entry.id === targetId)?.id ??
      null;

    if (diagramId) {
      setSelectedDiagramId(diagramId);
    }

    if (index.elementToModel[targetId]) {
      setSelectedElementId(targetId);
      setSelectedRelationId(null);
      return;
    }

    if (index.relationToModel[targetId]) {
      setSelectedRelationId(targetId);
      setSelectedElementId(null);
    }
  }

  async function runAutoLayout() {
    if (!selectedDiagramId) {
      return;
    }

    setBusy(true);
    try {
      setDiagram(await autoLayoutDiagram(selectedDiagramId));
      await loadWorkspace();
    } catch (layoutError) {
      setError(layoutError instanceof Error ? layoutError.message : "Could not auto layout diagram.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteSelectedFromModel(modelId: string, elementId: string) {
    const confirmed = window.confirm("Delete this element from the semantic model and all diagrams?");
    if (!confirmed) {
      return;
    }

    setBusy(true);
    try {
      await deleteElementFromModel(modelId, elementId);
      setSelectedElementId(null);
      if (selectedDiagramId) {
        setDiagram(await getDiagram(selectedDiagramId));
      }
      await loadWorkspace();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete element.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteRelationSelectedFromModel(modelId: string, relationId: string) {
    const confirmed = window.confirm("Delete this relation from the semantic model and all diagrams?");
    if (!confirmed) {
      return;
    }

    setBusy(true);
    try {
      await deleteRelationFromModel(modelId, relationId);
      setSelectedRelationId(null);
      if (selectedDiagramId) {
        setDiagram(await getDiagram(selectedDiagramId));
      }
      await loadWorkspace();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete relation.");
    } finally {
      setBusy(false);
    }
  }

  async function persistNodePosition(elementId: string, x: number, y: number) {
    if (!selectedDiagramId) {
      return;
    }

    try {
      await updateNodePosition(selectedDiagramId, elementId, x, y);
    } catch (layoutError) {
      setError(layoutError instanceof Error ? layoutError.message : "Could not save layout.");
    }
  }

  async function persistNodeResize(elementId: string, width: number, height: number) {
    if (!selectedDiagramId) {
      return;
    }

    try {
      await updateNodeLayout(selectedDiagramId, elementId, { width, height });
    } catch (layoutError) {
      setError(layoutError instanceof Error ? layoutError.message : "Could not save node size.");
    }
  }

  async function applyHistoryAction(action: "undo" | "redo") {
    setBusy(true);
    setError(null);
    try {
      const info = action === "undo" ? await undoWorkspace() : await redoWorkspace();
      setWorkspaceInfo(info);
      const nextDiagramId = selectedDiagramId ?? info.index.diagrams[0]?.id ?? null;
      setSelectedDiagramId(nextDiagramId);
      if (nextDiagramId) {
        setDiagram(await getDiagram(nextDiagramId));
      }
      setSelectedElementId(null);
      setSelectedRelationId(null);
    } catch (historyError) {
      setError(historyError instanceof Error ? historyError.message : `Could not ${action}.`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) {
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        deleteSelectedFromCanvas();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z" && !event.shiftKey) {
        event.preventDefault();
        void applyHistoryAction("undo");
      }
      if ((event.ctrlKey || event.metaKey) && (event.key.toLowerCase() === "y" || (event.key.toLowerCase() === "z" && event.shiftKey))) {
        event.preventDefault();
        void applyHistoryAction("redo");
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") {
        event.preventDefault();
        if (selectedElementId) {
          void duplicateSelectedElement();
        }
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void loadWorkspace();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedElementId, duplicateSelectedElement, loadWorkspace]);

  async function importExternalDiagram(input: { format: "plantuml" | "mermaid"; name: string; source: string }) {
    setBusy(true);
    setError(null);
    try {
      const imported = await importDiagramAsProposal({
        format: input.format,
        name: input.name.trim() || undefined,
        source: input.source
      });
      const info = await getWorkspaceInfo();
      setWorkspaceInfo(info);
      setLastRevision(info.revision ?? null);
      setSelectedProposalId(imported.proposal.id);
      setImportDiagramOpen(false);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Could not import diagram.");
    } finally {
      setBusy(false);
    }
  }

  async function exportCurrentDiagram(format: "plantuml" | "mermaid") {
    if (!selectedDiagramId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await exportDiagramSource(selectedDiagramId, format);
      setExportResult(result);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Could not export diagram.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Boxes size={22} aria-hidden />
          <div>
            <strong>AIaGMW</strong>
            <span>{workspaceInfo?.workspace?.name ?? "No workspace loaded"}</span>
          </div>
        </div>
        <div className="topbar-actions">
          <span className={busy ? "status busy" : "status"}>
            {busy ? <RefreshCw size={16} aria-hidden /> : <CheckCircle2 size={16} aria-hidden />}
            {busy ? "Working" : "Ready"}
          </span>
          <button
            type="button"
            className="icon-button"
            title={workspaceInfo?.history?.nextUndoLabel ? `Undo: ${workspaceInfo.history.nextUndoLabel}` : "Undo"}
            disabled={!workspaceInfo?.history?.undoCount}
            onClick={() => void applyHistoryAction("undo")}
          >
            <Undo2 size={17} aria-hidden />
          </button>
          <button
            type="button"
            className="icon-button"
            title={workspaceInfo?.history?.nextRedoLabel ? `Redo: ${workspaceInfo.history.nextRedoLabel}` : "Redo"}
            disabled={!workspaceInfo?.history?.redoCount}
            onClick={() => void applyHistoryAction("redo")}
          >
            <Redo2 size={17} aria-hidden />
          </button>
          <button type="button" className="icon-button" title="Open workspace" onClick={() => setOpenWorkspaceOpen(true)}>
            <FolderOpen size={17} aria-hidden />
          </button>
          <button type="button" className="icon-button" title="Create workspace" onClick={() => setCreateWorkspaceOpen(true)}>
            <Plus size={17} aria-hidden />
          </button>
          <button type="button" className="icon-button" title="Import PlantUML or Mermaid" onClick={() => setImportDiagramOpen(true)}>
            <Upload size={17} aria-hidden />
          </button>
          <button
            type="button"
            className="icon-button"
            title="Export selected diagram"
            disabled={!selectedDiagramId}
            onClick={() => {
              setExportResult(null);
              setExportDiagramOpen(true);
            }}
          >
            <Download size={17} aria-hidden />
          </button>
          <button type="button" className="icon-button" title="Reload workspace" onClick={() => void loadWorkspace()}>
            <RefreshCw size={17} aria-hidden />
          </button>
        </div>
      </header>

      <main className="workspace-grid">
        <aside className="sidebar">
          <div className="panel-title">
            <FolderOpen size={16} aria-hidden />
            <span>Workspace</span>
          </div>
          <WorkspaceExplorer
            info={workspaceInfo}
            selectedDiagramId={selectedDiagramId}
            onSelectDiagram={setSelectedDiagramId}
            onCreateModel={() => setCreateModelOpen(true)}
            onCreateDiagram={openCreateDiagramDialog}
            canCreateDiagram={Boolean(workspaceInfo?.index.models.length)}
          />
        </aside>

        <section className="center-stage">
          <div className="canvas-toolbar">
            <div className="toolbar-group">
              <button
                type="button"
                title="Add existing element"
                disabled={!selectedDiagramId || !existingElementOptions.length}
                onClick={openAddExistingElementDialog}
              >
                <Plus size={15} aria-hidden />
                element
              </button>
              <button
                type="button"
                title="Add existing relation"
                disabled={!selectedDiagramId || !existingRelationOptions.length}
                onClick={openAddExistingRelationDialog}
              >
                <Plus size={15} aria-hidden />
                relation
              </button>
              {palette.elementKinds.map((kind) => (
                <button key={kind} type="button" title={`Add ${kind}`} onClick={() => void addElement(kind)}>
                  <Plus size={15} aria-hidden />
                  {kind.replaceAll("_", " ")}
                </button>
              ))}
              <button type="button" title="Auto layout (grid)" disabled={!selectedDiagramId} onClick={() => void runAutoLayout()}>
                <Grid3x3 size={15} aria-hidden />
                layout
              </button>
            </div>
            <div className="toolbar-group relation-tools" aria-label="Relation kind">
              {palette.relationKinds.map((kind) => (
                <button
                  key={kind}
                  type="button"
                  className={kind === selectedRelationKind ? "active-tool" : ""}
                  title={`Use ${kind} relation`}
                  onClick={() => setSelectedRelationKind(kind)}
                >
                  {kind}
                </button>
              ))}
            </div>
            <div className="toolbar-hint">
              <Activity size={15} aria-hidden />
              <span>
                {diagram
                  ? `${diagram.elements.length} elements, ${diagram.relations.length} relations - drag handles to create ${selectedRelationKind}`
                  : "No diagram"}
              </span>
            </div>
          </div>

          <DiagramRouter
            detail={diagram}
            selectedElementId={selectedElementId}
            selectedRelationId={selectedRelationId}
            diffPreview={diffPreview}
            onSelectElement={setSelectedElementId}
            onSelectRelation={setSelectedRelationId}
            onMoveNode={(elementId, x, y) => void persistNodePosition(elementId, x, y)}
            onResizeNode={(elementId, width, height) => void persistNodeResize(elementId, width, height)}
            onCreateRelation={(from, to) => void addRelation(from, to)}
            onDeleteSelected={deleteSelectedFromCanvas}
            onDuplicateSelected={() => void duplicateSelectedElement()}
          />
        </section>

        <aside className="inspector">
          <div className="panel-title">
            <Save size={16} aria-hidden />
            <span>Inspector</span>
          </div>
          <Inspector
            element={selectedElement}
            relation={selectedRelation}
            onSaveElement={(modelId, elementId, updates) => void saveElement(modelId, elementId, updates)}
            onSaveRelation={(modelId, relationId, updates) => void saveRelation(modelId, relationId, updates)}
            onRemoveElementFromDiagram={(modelId, elementId) => void removeSelectedFromDiagram(modelId, elementId)}
            onDeleteElementFromModel={(modelId, elementId) => void deleteSelectedFromModel(modelId, elementId)}
            onRemoveRelationFromDiagram={(modelId, relationId) => void removeRelationSelectedFromDiagram(modelId, relationId)}
            onDeleteRelationFromModel={(modelId, relationId) => void deleteRelationSelectedFromModel(modelId, relationId)}
          />
        </aside>
      </main>

      <footer className="bottom-panel">
        <section>
          <div className="panel-title">
            <CircleAlert size={16} aria-hidden />
            <span>Diagnostics</span>
          </div>
          <DiagnosticsPanel diagnostics={diagnostics} onNavigate={navigateDiagnostic} />
        </section>
        <section>
          <div className="panel-title">
            <Bot size={16} aria-hidden />
            <span>Proposals</span>
          </div>
          <ProposalReviewPanel
            proposals={workspaceInfo?.index.proposals ?? []}
            selectedProposalId={selectedProposalId}
            onSelectProposal={setSelectedProposalId}
            onChanged={loadWorkspace}
            onPreviewDiff={setDiffPreview}
          />
        </section>
      </footer>

      <CreateDiagramDialog
        open={createDiagramOpen}
        models={workspaceInfo?.index.models ?? []}
        busy={busy}
        onCancel={() => setCreateDiagramOpen(false)}
        onCreate={(input) => void addDiagram(input)}
      />
      <CreateModelDialog
        open={createModelOpen}
        busy={busy}
        onCancel={() => setCreateModelOpen(false)}
        onCreate={(input) => void addModel(input)}
      />
      <AddExistingElementDialog
        open={addExistingElementOpen}
        elements={existingElementOptions}
        busy={busy}
        onCancel={() => setAddExistingElementOpen(false)}
        onAdd={(elementId) => void addExistingElement(elementId)}
      />
      <AddExistingRelationDialog
        open={addExistingRelationOpen}
        relations={existingRelationOptions}
        busy={busy}
        onCancel={() => setAddExistingRelationOpen(false)}
        onAdd={(relationId) => void addExistingRelation(relationId)}
      />
      <WorkspacePathDialog
        open={openWorkspaceOpen}
        title="Open workspace"
        submitLabel="Open"
        busy={busy}
        onCancel={() => setOpenWorkspaceOpen(false)}
        onSubmit={async (path) => {
          setBusy(true);
          try {
            const info = await openWorkspace(path);
            setWorkspaceInfo(info);
            setLastRevision(info.revision ?? null);
            setSelectedDiagramId(info.index.diagrams[0]?.id ?? null);
            setOpenWorkspaceOpen(false);
          } catch (openError) {
            setError(openError instanceof Error ? openError.message : "Could not open workspace.");
          } finally {
            setBusy(false);
          }
        }}
      />
      <CreateWorkspaceDialog
        open={createWorkspaceOpen}
        busy={busy}
        onCancel={() => setCreateWorkspaceOpen(false)}
        onCreate={async (input) => {
          setBusy(true);
          try {
            const info = await createWorkspace(input);
            setWorkspaceInfo(info);
            setLastRevision(info.revision ?? null);
            setSelectedDiagramId(info.index.diagrams[0]?.id ?? null);
            setCreateWorkspaceOpen(false);
          } catch (createError) {
            setError(createError instanceof Error ? createError.message : "Could not create workspace.");
          } finally {
            setBusy(false);
          }
        }}
      />
      <ImportDiagramDialog
        open={importDiagramOpen}
        busy={busy}
        onCancel={() => setImportDiagramOpen(false)}
        onPreview={(input) => importDiagramPreview(input)}
        onImport={(input) => void importExternalDiagram(input)}
      />
      <ExportDiagramDialog
        open={exportDiagramOpen}
        busy={busy}
        result={exportResult}
        onCancel={() => {
          setExportDiagramOpen(false);
          setExportResult(null);
        }}
        onExport={(format) => void exportCurrentDiagram(format)}
      />
    </div>
  );
}

function endpointId(value: string): string {
  const index = value.indexOf("#");
  return index >= 0 ? value.slice(index + 1) : value;
}

interface ImportDiagramDialogProps {
  open: boolean;
  busy: boolean;
  onCancel: () => void;
  onPreview: (input: { format: "plantuml" | "mermaid"; name: string; source: string }) => Promise<ImportDiagramPreviewResponse>;
  onImport: (input: { format: "plantuml" | "mermaid"; name: string; source: string }) => void;
}

function ImportDiagramDialog({ open, busy, onCancel, onPreview, onImport }: ImportDiagramDialogProps) {
  const [format, setFormat] = useState<"plantuml" | "mermaid">("plantuml");
  const [name, setName] = useState("Imported Model");
  const [source, setSource] = useState(samplePlantUml);
  const [preview, setPreview] = useState<ImportDiagramPreviewResponse | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setFormat("plantuml");
      setName("Imported Model");
      setSource(samplePlantUml);
      setPreview(null);
      setPreviewError(null);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  const canImport = Boolean(source.trim()) && preview?.applicable;

  async function handlePreview() {
    if (!source.trim()) {
      return;
    }
    setPreviewBusy(true);
    setPreviewError(null);
    try {
      setPreview(
        await onPreview({
          format,
          name,
          source
        })
      );
    } catch (error) {
      setPreview(null);
      setPreviewError(error instanceof Error ? error.message : "Could not preview import.");
    } finally {
      setPreviewBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog wide-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="import-diagram-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (canImport) {
            onImport({ format, name, source });
          }
        }}
      >
        <div className="dialog-title">
          <h2 id="import-diagram-title">Import diagram</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy || previewBusy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
        </label>

        <label>
          Format
          <select
            value={format}
            onChange={(event) => {
              const next = event.target.value as "plantuml" | "mermaid";
              setFormat(next);
              setSource(next === "plantuml" ? samplePlantUml : sampleMermaid);
              setPreview(null);
            }}
          >
            <option value="plantuml">PlantUML</option>
            <option value="mermaid">Mermaid</option>
          </select>
        </label>

        <label>
          Source
          <textarea value={source} onChange={(event) => {
            setSource(event.target.value);
            setPreview(null);
          }} spellCheck={false} />
        </label>

        {preview ? (
          <div className="import-preview-summary">
            <strong>Preview</strong>
            <span>
              {preview.imported.elements} elements, {preview.imported.relations} relations — proposal {preview.proposal.id}
            </span>
            <span className={preview.applicable ? "status applicable" : "status blocked"}>
              {preview.applicable ? "Applicable" : "Blocked"}
            </span>
          </div>
        ) : null}
        {previewError ? <p className="proposal-error">{previewError}</p> : null}

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy || previewBusy}>
            Cancel
          </button>
          <button type="button" className="secondary-action" disabled={!source.trim() || busy || previewBusy} onClick={() => void handlePreview()}>
            Preview
          </button>
          <button type="submit" disabled={!canImport || busy || previewBusy}>
            <Upload size={15} aria-hidden />
            Submit proposal
          </button>
        </div>
      </form>
    </div>
  );
}

interface ExportDiagramDialogProps {
  open: boolean;
  busy: boolean;
  result: { format: "plantuml" | "mermaid"; path: string; source: string } | null;
  onCancel: () => void;
  onExport: (format: "plantuml" | "mermaid") => void;
}

function ExportDiagramDialog({ open, busy, result, onCancel, onExport }: ExportDiagramDialogProps) {
  const [format, setFormat] = useState<"plantuml" | "mermaid">("plantuml");

  useEffect(() => {
    if (open) {
      setFormat("plantuml");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog wide-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="export-diagram-title"
        onSubmit={(event) => {
          event.preventDefault();
          onExport(format);
        }}
      >
        <div className="dialog-title">
          <h2 id="export-diagram-title">Export diagram</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Format
          <select value={format} onChange={(event) => setFormat(event.target.value as "plantuml" | "mermaid")}>
            <option value="plantuml">PlantUML</option>
            <option value="mermaid">Mermaid</option>
          </select>
        </label>

        {result ? (
          <label>
            {result.path}
            <textarea value={result.source} readOnly spellCheck={false} />
          </label>
        ) : null}

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Close
          </button>
          <button type="submit" disabled={busy}>
            <Download size={15} aria-hidden />
            Export
          </button>
        </div>
      </form>
    </div>
  );
}

const samplePlantUml = `@startuml
title Imported Model
class Browser
interface KnowledgeStore
class ModelingWorkspace
Browser --> KnowledgeStore : searches
ModelingWorkspace ..> KnowledgeStore : imports context
@enduml`;

const sampleMermaid = `%% title: Imported Flow
flowchart LR
  Browser["UML Browser"] --> DB["Knowledge DB"]
  DB --> Workspace["Modeling Workspace"]`;

interface CreateModelDialogProps {
  open: boolean;
  busy: boolean;
  onCancel: () => void;
  onCreate: (input: { name: string; modelType: ModelType }) => void;
}

function CreateModelDialog({ open, busy, onCancel, onCreate }: CreateModelDialogProps) {
  const [name, setName] = useState("New Model");
  const [modelType, setModelType] = useState<ModelType>("class-model");

  useEffect(() => {
    if (open) {
      setName("New Model");
      setModelType("class-model");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  const canCreate = Boolean(name.trim());

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="create-model-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (canCreate) {
            onCreate({ name, modelType });
          }
        }}
      >
        <div className="dialog-title">
          <h2 id="create-model-title">Create model</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
        </label>

        <label>
          Type
          <select value={modelType} onChange={(event) => setModelType(event.target.value as ModelType)}>
            {modelTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!canCreate || busy}>
            <Plus size={15} aria-hidden />
            Create
          </button>
        </div>
      </form>
    </div>
  );
}

interface ExistingElementOption {
  id: string;
  name: string;
  kind: ElementKind;
  modelName: string;
}

interface AddExistingElementDialogProps {
  open: boolean;
  elements: ExistingElementOption[];
  busy: boolean;
  onCancel: () => void;
  onAdd: (elementId: string) => void;
}

function AddExistingElementDialog({ open, elements, busy, onCancel, onAdd }: AddExistingElementDialogProps) {
  const [elementId, setElementId] = useState("");

  useEffect(() => {
    if (open) {
      setElementId(elements[0]?.id ?? "");
    }
  }, [elements, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="add-existing-element-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (elementId) {
            onAdd(elementId);
          }
        }}
      >
        <div className="dialog-title">
          <h2 id="add-existing-element-title">Add existing element</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Element
          <select value={elementId} onChange={(event) => setElementId(event.target.value)}>
            {elements.map((element) => (
              <option key={element.id} value={element.id}>
                {element.name} ({element.kind}, {element.modelName})
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!elementId || busy}>
            <Plus size={15} aria-hidden />
            Add
          </button>
        </div>
      </form>
    </div>
  );
}

interface ExistingRelationOption {
  id: string;
  name: string;
  kind: RelationKind;
  from: string;
  to: string;
  fromName: string;
  toName: string;
  modelName: string;
}

interface AddExistingRelationDialogProps {
  open: boolean;
  relations: ExistingRelationOption[];
  busy: boolean;
  onCancel: () => void;
  onAdd: (relationId: string) => void;
}

function AddExistingRelationDialog({ open, relations, busy, onCancel, onAdd }: AddExistingRelationDialogProps) {
  const [relationId, setRelationId] = useState("");

  useEffect(() => {
    if (open) {
      setRelationId(relations[0]?.id ?? "");
    }
  }, [open, relations]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="add-existing-relation-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (relationId) {
            onAdd(relationId);
          }
        }}
      >
        <div className="dialog-title">
          <h2 id="add-existing-relation-title">Add existing relation</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Relation
          <select value={relationId} onChange={(event) => setRelationId(event.target.value)}>
            {relations.map((relation) => (
              <option key={relation.id} value={relation.id}>
                {relation.name} ({relation.fromName} {"->"} {relation.toName}, {relation.modelName})
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!relationId || busy}>
            <Plus size={15} aria-hidden />
            Add
          </button>
        </div>
      </form>
    </div>
  );
}

interface CreateDiagramDialogProps {
  open: boolean;
  models: WorkspaceInfoResponse["index"]["models"];
  busy: boolean;
  onCancel: () => void;
  onCreate: (input: { name: string; diagramType: DiagramType; modelId: string }) => void;
}

function CreateDiagramDialog({ open, models, busy, onCancel, onCreate }: CreateDiagramDialogProps) {
  const [name, setName] = useState("New Class Diagram");
  const [diagramType, setDiagramType] = useState<DiagramType>("class");
  const [modelId, setModelId] = useState("");

  useEffect(() => {
    if (open) {
      setName("New Class Diagram");
      setDiagramType("class");
      setModelId(models[0]?.id ?? "");
    }
  }, [models, open]);

  if (!open) {
    return null;
  }

  const canCreate = Boolean(name.trim() && modelId);

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        aria-modal="true"
        role="dialog"
        aria-labelledby="create-diagram-title"
        onSubmit={(event) => {
          event.preventDefault();
          if (canCreate) {
            onCreate({ name, diagramType, modelId });
          }
        }}
      >
        <div className="dialog-title">
          <h2 id="create-diagram-title">Create diagram</h2>
          <button type="button" className="icon-button" title="Close" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>

        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
        </label>

        <label>
          Model
          <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Type
          <select value={diagramType} onChange={(event) => setDiagramType(event.target.value as DiagramType)}>
            {diagramTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!canCreate || busy}>
            <Plus size={15} aria-hidden />
            Create
          </button>
        </div>
      </form>
    </div>
  );
}

interface WorkspacePathDialogProps {
  open: boolean;
  title: string;
  submitLabel: string;
  busy: boolean;
  onCancel: () => void;
  onSubmit: (path: string) => void;
}

function WorkspacePathDialog({ open, title, submitLabel, busy, onCancel, onSubmit }: WorkspacePathDialogProps) {
  const [path, setPath] = useState("demo-workspace");

  useEffect(() => {
    if (open) {
      setPath("demo-workspace");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (path.trim()) {
            onSubmit(path.trim());
          }
        }}
      >
        <div className="dialog-title">
          <h2>{title}</h2>
          <button type="button" className="icon-button" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>
        <label>
          Workspace path (relative to workspaces parent)
          <input value={path} onChange={(event) => setPath(event.target.value)} autoFocus />
        </label>
        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!path.trim() || busy}>
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}

interface CreateWorkspaceDialogProps {
  open: boolean;
  busy: boolean;
  onCancel: () => void;
  onCreate: (input: { path: string; id: string; name: string; description?: string }) => void;
}

function CreateWorkspaceDialog({ open, busy, onCancel, onCreate }: CreateWorkspaceDialogProps) {
  const [path, setPath] = useState("demo-workspace");
  const [id, setId] = useState("workspace.demo");
  const [name, setName] = useState("Demo Workspace");

  useEffect(() => {
    if (open) {
      setPath("demo-workspace");
      setId("workspace.demo");
      setName("Demo Workspace");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="creation-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate({ path: path.trim(), id: id.trim(), name: name.trim() });
        }}
      >
        <div className="dialog-title">
          <h2>Create workspace</h2>
          <button type="button" className="icon-button" onClick={onCancel} disabled={busy}>
            <X size={16} aria-hidden />
          </button>
        </div>
        <label>
          Folder path
          <input value={path} onChange={(event) => setPath(event.target.value)} autoFocus />
        </label>
        <label>
          Workspace ID
          <input value={id} onChange={(event) => setId(event.target.value)} />
        </label>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <div className="dialog-actions">
          <button type="button" className="secondary-action" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="submit" disabled={!path.trim() || !id.trim() || !name.trim() || busy}>
            Create
          </button>
        </div>
      </form>
    </div>
  );
}
