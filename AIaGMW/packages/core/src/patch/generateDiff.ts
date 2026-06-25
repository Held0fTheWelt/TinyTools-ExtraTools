import type { PatchProposal, UmlDiagram, UmlElement, UmlLayout, UmlModel, UmlRelation } from "@aiagmw/shared";
import type { WorkspaceState } from "../workspace";

export interface PatchDiff {
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

export function generateDiff(before: WorkspaceState, after: WorkspaceState, proposal: PatchProposal): PatchDiff {
  const diff: PatchDiff = {
    addedElements: [],
    removedElements: [],
    updatedElements: [],
    addedRelations: [],
    removedRelations: [],
    updatedRelations: [],
    addedDiagrams: [],
    updatedDiagrams: [],
    layoutChanges: [],
    affectedModelIds: [],
    affectedDiagramIds: []
  };

  const beforeModels = new Map(before.models.map((entry) => [entry.data.id, entry.data]));
  const afterModels = new Map(after.models.map((entry) => [entry.data.id, entry.data]));

  for (const [modelId, afterModel] of afterModels) {
    const beforeModel = beforeModels.get(modelId);
    if (!beforeModel) {
      diff.affectedModelIds.push(modelId);
      diff.addedElements.push(...afterModel.elements.map((element) => ({ modelId, element })));
      diff.addedRelations.push(...afterModel.relations.map((relation) => ({ modelId, relation })));
      continue;
    }

    diffElements(modelId, beforeModel, afterModel, diff);
    diffRelations(modelId, beforeModel, afterModel, diff);
  }

  for (const [modelId, beforeModel] of beforeModels) {
    if (!afterModels.has(modelId)) {
      diff.affectedModelIds.push(modelId);
      diff.removedElements.push(...beforeModel.elements.map((element) => ({ modelId, element })));
      diff.removedRelations.push(...beforeModel.relations.map((relation) => ({ modelId, relation })));
    }
  }

  const beforeDiagrams = new Map(before.diagrams.map((entry) => [entry.data.id, entry.data]));
  const afterDiagrams = new Map(after.diagrams.map((entry) => [entry.data.id, entry.data]));

  for (const [diagramId, afterDiagram] of afterDiagrams) {
    const beforeDiagram = beforeDiagrams.get(diagramId);
    if (!beforeDiagram) {
      diff.addedDiagrams.push(afterDiagram);
      diff.affectedDiagramIds.push(diagramId);
      continue;
    }
    if (JSON.stringify(beforeDiagram) !== JSON.stringify(afterDiagram)) {
      diff.updatedDiagrams.push({ diagramId, before: beforeDiagram, after: afterDiagram });
      diff.affectedDiagramIds.push(diagramId);
    }
  }

  const beforeLayouts = new Map(before.layouts.map((entry) => [entry.data.diagramId, entry.data]));
  const afterLayouts = new Map(after.layouts.map((entry) => [entry.data.diagramId, entry.data]));

  for (const [diagramId, afterLayout] of afterLayouts) {
    const beforeLayout = beforeLayouts.get(diagramId);
    diffLayout(diagramId, beforeLayout, afterLayout, diff);
  }

  for (const operation of proposal.operations) {
    if (operation.modelId && !diff.affectedModelIds.includes(operation.modelId)) {
      diff.affectedModelIds.push(operation.modelId);
    }
    if (operation.diagramId && !diff.affectedDiagramIds.includes(operation.diagramId)) {
      diff.affectedDiagramIds.push(operation.diagramId);
    }
  }

  return diff;
}

function diffElements(modelId: string, beforeModel: UmlModel, afterModel: UmlModel, diff: PatchDiff) {
  const beforeElements = new Map(beforeModel.elements.map((element) => [element.id, element]));
  const afterElements = new Map(afterModel.elements.map((element) => [element.id, element]));

  for (const [elementId, afterElement] of afterElements) {
    const beforeElement = beforeElements.get(elementId);
    if (!beforeElement) {
      diff.addedElements.push({ modelId, element: afterElement });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
      continue;
    }
    if (JSON.stringify(beforeElement) !== JSON.stringify(afterElement)) {
      diff.updatedElements.push({ modelId, elementId, before: beforeElement, after: afterElement });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
    }
  }

  for (const [elementId, beforeElement] of beforeElements) {
    if (!afterElements.has(elementId)) {
      diff.removedElements.push({ modelId, element: beforeElement });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
    }
  }
}

function diffRelations(modelId: string, beforeModel: UmlModel, afterModel: UmlModel, diff: PatchDiff) {
  const beforeRelations = new Map(beforeModel.relations.map((relation) => [relation.id, relation]));
  const afterRelations = new Map(afterModel.relations.map((relation) => [relation.id, relation]));

  for (const [relationId, afterRelation] of afterRelations) {
    const beforeRelation = beforeRelations.get(relationId);
    if (!beforeRelation) {
      diff.addedRelations.push({ modelId, relation: afterRelation });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
      continue;
    }
    if (JSON.stringify(beforeRelation) !== JSON.stringify(afterRelation)) {
      diff.updatedRelations.push({ modelId, relationId, before: beforeRelation, after: afterRelation });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
    }
  }

  for (const [relationId, beforeRelation] of beforeRelations) {
    if (!afterRelations.has(relationId)) {
      diff.removedRelations.push({ modelId, relation: beforeRelation });
      if (!diff.affectedModelIds.includes(modelId)) {
        diff.affectedModelIds.push(modelId);
      }
    }
  }
}

function diffLayout(diagramId: string, beforeLayout: UmlLayout | undefined, afterLayout: UmlLayout, diff: PatchDiff) {
  const beforeNodes = beforeLayout?.nodes ?? {};
  const afterNodes = afterLayout.nodes;
  const nodeIds = new Set([...Object.keys(beforeNodes), ...Object.keys(afterNodes)]);

  for (const elementId of nodeIds) {
    const beforeNode = beforeNodes[elementId];
    const afterNode = afterNodes[elementId];
    if (JSON.stringify(beforeNode ?? null) !== JSON.stringify(afterNode ?? null)) {
      diff.layoutChanges.push({
        diagramId,
        elementId,
        before: beforeNode as Record<string, unknown> | undefined,
        after: afterNode as Record<string, unknown> | undefined
      });
      if (!diff.affectedDiagramIds.includes(diagramId)) {
        diff.affectedDiagramIds.push(diagramId);
      }
    }
  }
}
