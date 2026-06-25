import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  NodeResizer,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type OnConnect,
  type NodeProps,
  type OnNodeDrag
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { DiagramDetail, PatchPreviewResponse, RelationKind, UmlElement } from "@aiagmw/shared";
import { buildDiffElementStates, endpointId, formatParameters, nodeClassName, relationLabel, visibilitySymbol } from "./diagramViewModel";

export type DiagramCanvasVariant = "class" | "component" | "sequence" | "state" | "activity" | "deployment";

export interface BaseDiagramCanvasProps {
  variant?: DiagramCanvasVariant;
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

type UmlNodeData = {
  element: UmlElement & { modelId: string };
  diffState?: "added" | "removed" | "updated";
  variant: DiagramCanvasVariant;
  onResizeNode?: (elementId: string, width: number, height: number) => void;
};

interface ContextMenuState {
  x: number;
  y: number;
  elementId: string | null;
}

const nodeTypes = {
  uml: UmlNode
};

function UmlNode({ data, selected }: NodeProps<Node<UmlNodeData>>) {
  const element = data.element;
  const stereotypes = element.stereotypes?.length ? `<<${element.stereotypes.join(", ")}>>` : "";
  const compact = data.variant === "sequence" || data.variant === "state" || data.variant === "activity";

  return (
    <div className={nodeClassName(element, selected, data.diffState, data.variant)}>
      {!compact ? (
        <NodeResizer
          minWidth={180}
          minHeight={100}
          isVisible={selected}
          onResizeEnd={(_, params) => data.onResizeNode?.(element.id, params.width, params.height)}
        />
      ) : null}
      <Handle type="target" position={data.variant === "sequence" ? Position.Top : Position.Left} className="uml-handle" />
      <Handle type="source" position={data.variant === "sequence" ? Position.Bottom : Position.Right} className="uml-handle" />
      <div className="uml-title">
        {stereotypes ? <span className="stereotype">{stereotypes}</span> : null}
        <strong className={element.abstract ? "abstract-name" : ""}>{element.name}</strong>
        <span>{element.kind.replaceAll("_", " ")}</span>
      </div>
      {!compact ? (
        <>
          <div className="uml-compartment">
            {(element.properties ?? []).slice(0, 4).map((property) => (
              <span key={`${element.id}-property-${property.name}`}>
                {visibilitySymbol(property.visibility)}
                {property.name}: {property.type ?? "any"}
                {property.multiplicity ? ` [${property.multiplicity}]` : ""}
              </span>
            ))}
            {(element.properties ?? []).length === 0 ? <span className="muted">No properties</span> : null}
          </div>
          <div className="uml-compartment">
            {(element.methods ?? []).slice(0, 4).map((method) => (
              <span key={`${element.id}-method-${method.name}`}>
                {visibilitySymbol(method.visibility)}
                {method.name}({formatParameters(method.parameters)}): {method.returnType ?? "void"}
              </span>
            ))}
            {(element.methods ?? []).length === 0 ? <span className="muted">No methods</span> : null}
          </div>
        </>
      ) : null}
      {element.kind === "enum" && element.constraints?.length ? (
        <div className="uml-compartment">
          {element.constraints.slice(0, 6).map((literal) => (
            <span key={`${element.id}-literal-${literal}`}>{literal}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function BaseDiagramCanvas({
  variant = "class",
  detail,
  selectedElementId,
  selectedRelationId,
  diffPreview,
  onSelectElement,
  onSelectRelation,
  onMoveNode,
  onResizeNode,
  onCreateRelation,
  onDeleteSelected,
  onDuplicateSelected
}: BaseDiagramCanvasProps) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const diffElementStates = useMemo(() => buildDiffElementStates(diffPreview), [diffPreview]);

  const defaultPosition = useCallback(
    (element: UmlElement, index: number, layout?: { x?: number; y?: number }) => {
      if (layout?.x !== undefined && layout?.y !== undefined) {
        return { x: layout.x, y: layout.y };
      }

      if (variant === "sequence") {
        return { x: 120 + index * 220, y: element.kind === "activation" ? 220 : 80 };
      }
      if (variant === "state" || variant === "activity") {
        return { x: 140 + (index % 4) * 240, y: 120 + Math.floor(index / 4) * 160 };
      }
      if (variant === "deployment") {
        return { x: 120 + (index % 3) * 300, y: 100 + Math.floor(index / 3) * 220 };
      }
      return {
        x: 120 + index * 280,
        y: 140 + (index % 3) * 180
      };
    },
    [variant]
  );

  const nodes = useMemo<Node<UmlNodeData>[]>(() => {
    if (!detail) {
      return [];
    }

    return detail.elements.map((element, index) => {
      const layout = detail.layout.nodes[element.id];
      const position = defaultPosition(element, index, layout);
      const isSequenceLifeline = variant === "sequence" && element.kind === "lifeline";
      const isStateNode = variant === "state" && (element.kind === "state_node" || element.kind === "final_state");
      const isActivityNode = variant === "activity" && element.kind === "action";

      return {
        id: element.id,
        type: "uml",
        position,
        data: {
          element,
          diffState: diffElementStates.get(element.id),
          variant,
          onResizeNode
        },
        selected: element.id === selectedElementId,
        style: {
          width: layout?.width ?? (isSequenceLifeline ? 120 : isStateNode ? 180 : isActivityNode ? 200 : 260),
          height: layout?.height ?? (isSequenceLifeline ? 320 : isStateNode ? 80 : isActivityNode ? 72 : 150)
        }
      };
    });
  }, [detail, diffElementStates, selectedElementId, onResizeNode, variant, defaultPosition]);

  const edges = useMemo<Edge[]>(() => {
    if (!detail) {
      return [];
    }

    const elementIds = new Set(detail.elements.map((element) => element.id));
    return detail.relations
      .filter((relation) => elementIds.has(endpointId(relation.from)) && elementIds.has(endpointId(relation.to)))
      .map((relation) => ({
        id: relation.id,
        source: endpointId(relation.from),
        target: endpointId(relation.to),
        label: relationLabel(relation),
        type: variant === "sequence" ? "straight" : "smoothstep",
        markerStart: markerStartForRelation(relation.kind),
        markerEnd: markerEndForRelation(relation.kind),
        style: styleForRelation(relation.kind, variant),
        selected: relation.id === selectedRelationId,
        className: relation.id === selectedRelationId ? "uml-edge selected" : "uml-edge"
      }));
  }, [detail, selectedRelationId, variant]);

  const handleNodeDragStop: OnNodeDrag = (_, node) => {
    onMoveNode(node.id, node.position.x, node.position.y);
  };

  const handleConnect: OnConnect = (connection) => {
    if (connection.source && connection.target) {
      onCreateRelation(connection.source, connection.target);
    }
  };

  useEffect(() => {
    if (!contextMenu) {
      return;
    }

    const close = () => setContextMenu(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, [contextMenu]);

  if (!detail) {
    return (
      <div className="empty-canvas">
        <strong>No diagram selected</strong>
        <span>Open a diagram from the workspace explorer.</span>
      </div>
    );
  }

  return (
    <div className={`diagram-canvas diagram-canvas-${variant}`} onContextMenu={(event) => event.preventDefault()}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.35}
        maxZoom={1.7}
        multiSelectionKeyCode="Shift"
        onNodeClick={(_, node) => {
          onSelectRelation(null);
          onSelectElement(node.id);
        }}
        onEdgeClick={(_, edge) => {
          onSelectElement(null);
          onSelectRelation(edge.id);
        }}
        onPaneClick={() => {
          onSelectElement(null);
          onSelectRelation(null);
          setContextMenu(null);
        }}
        onPaneContextMenu={(event) => {
          if (selectedElementId) {
            event.preventDefault();
            setContextMenu({ x: event.clientX, y: event.clientY, elementId: selectedElementId });
          }
        }}
        onNodeContextMenu={(event, node) => {
          event.preventDefault();
          onSelectRelation(null);
          onSelectElement(node.id);
          setContextMenu({ x: event.clientX, y: event.clientY, elementId: node.id });
        }}
        onNodeDragStop={handleNodeDragStop}
        onConnect={handleConnect}
      >
        <Background color="#d9dee7" gap={18} />
        <MiniMap pannable zoomable nodeStrokeWidth={3} />
        <Controls />
      </ReactFlow>

      {contextMenu ? (
        <div className="canvas-context-menu" style={{ top: contextMenu.y, left: contextMenu.x }}>
          <button
            type="button"
            onClick={() => {
              onDuplicateSelected?.();
              setContextMenu(null);
            }}
          >
            Duplicate
          </button>
          <button
            type="button"
            className="danger-action"
            onClick={() => {
              onDeleteSelected?.();
              setContextMenu(null);
            }}
          >
            Delete
          </button>
        </div>
      ) : null}
    </div>
  );
}

function markerEndForRelation(kind: RelationKind) {
  if (kind === "inheritance" || kind === "transition") {
    return { type: MarkerType.ArrowClosed, color: "#111827", width: 18, height: 18 };
  }
  if (kind === "implementation" || kind === "realization") {
    return { type: MarkerType.ArrowClosed, color: "#334155", width: 16, height: 16 };
  }
  if (kind === "composition" || kind === "destroy") {
    return { type: MarkerType.ArrowClosed, color: "#111827", width: 16, height: 16 };
  }
  if (kind === "aggregation") {
    return { type: MarkerType.Arrow, color: "#475569", width: 16, height: 16 };
  }
  if (kind === "async_message") {
    return { type: MarkerType.Arrow, color: "#475569", width: 16, height: 16 };
  }
  return { type: MarkerType.ArrowClosed, color: "#475569", width: 16, height: 16 };
}

function markerStartForRelation(kind: RelationKind) {
  if (kind === "composition") {
    return { type: MarkerType.ArrowClosed, color: "#111827", width: 14, height: 14 };
  }
  if (kind === "aggregation") {
    return { type: MarkerType.Arrow, color: "#475569", width: 14, height: 14 };
  }
  return undefined;
}

function styleForRelation(kind: RelationKind, variant: DiagramCanvasVariant) {
  const dashed =
    kind === "dependency" ||
    kind === "implementation" ||
    kind === "realization" ||
    kind === "async_message" ||
    kind === "reply" ||
    kind === "object_flow";
  const heavy = kind === "composition" || kind === "aggregation" || kind === "deploy";
  const sequence = variant === "sequence";
  return {
    stroke: heavy ? "#111827" : sequence ? "#2563eb" : "#475569",
    strokeWidth: heavy ? 2.4 : sequence ? 2 : 1.6,
    strokeDasharray: dashed ? "7 5" : undefined
  };
}
