import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import type {
  AkdbDiagramSource,
  AkdbDiagramSummary,
  AkdbExportStageResult,
  ConnectorContext,
  ConnectorResult,
  Provenance
} from "../types";

export interface AkdbDiagramFilter {
  kind?: string;
  limit?: number;
  query?: string;
}

export interface AkdbConnector {
  fetchContextPack(task: string, projectId?: string): Promise<ConnectorResult<Record<string, unknown>>>;
  listNormativeDiagrams(projectId?: string, filter?: AkdbDiagramFilter): Promise<ConnectorResult<AkdbDiagramSummary[]>>;
  fetchDiagramSource(diagramId: string, projectId?: string): Promise<ConnectorResult<AkdbDiagramSource>>;
  exportAndStage(
    plantUmlSource: string,
    targetPath: string,
    provenance: Provenance
  ): Promise<ConnectorResult<AkdbExportStageResult>>;
}

function connectorDiagnostic(message: string, code = "connector.akdb.error") {
  return {
    level: "warning" as const,
    code,
    message,
    category: "connector"
  };
}

function resolveProjectId(context: ConnectorContext, projectId?: string): string {
  return (projectId ?? context.akdbProjectId).trim();
}

function resolveFetch(context: ConnectorContext): typeof fetch {
  return context.fetchImpl ?? fetch;
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text.trim()) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

function normalizeDiagram(row: Record<string, unknown>): AkdbDiagramSummary {
  return {
    diagramId: String(row.diagram_id ?? row.diagramId ?? ""),
    title: typeof row.title === "string" ? row.title : undefined,
    diagramKind: typeof row.diagram_kind === "string" ? row.diagram_kind : typeof row.diagramKind === "string" ? row.diagramKind : undefined,
    sourceUri: typeof row.source_uri === "string" ? row.source_uri : typeof row.sourceUri === "string" ? row.sourceUri : undefined,
    sourceKey: typeof row.source_key === "string" ? row.source_key : typeof row.sourceKey === "string" ? row.sourceKey : undefined,
    notation: typeof row.notation === "string" ? row.notation : undefined
  };
}

function resolveNotation(raw: Record<string, unknown>): "plantuml" | "mermaid" {
  const notation = typeof raw.notation === "string" ? raw.notation.toLowerCase() : "plantuml";
  return notation === "mermaid" ? "mermaid" : "plantuml";
}

function resolveSource(raw: Record<string, unknown>): string {
  const candidates = [raw.raw_source, raw.rawSource, raw.source, raw.rendered_source, raw.renderedSource];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  return "";
}

function matchesQuery(diagram: AkdbDiagramSummary, query?: string): boolean {
  if (!query?.trim()) {
    return true;
  }
  const normalized = query.trim().toLowerCase();
  const haystack = [diagram.diagramId, diagram.title, diagram.sourceKey, diagram.sourceUri, diagram.diagramKind]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(normalized);
}

export function createAkdbConnector(context: ConnectorContext): AkdbConnector {
  const baseUrl = context.akdbUrl.replace(/\/+$/, "");

  return {
    async fetchContextPack(task, projectId) {
      const resolvedProjectId = resolveProjectId(context, projectId);
      if (!task.trim()) {
        return {
          ok: false,
          error: "Task is required.",
          diagnostics: [connectorDiagnostic("AKDB context pack task is required.", "connector.akdb.task_required")]
        };
      }

      try {
        const response = await resolveFetch(context)(`${baseUrl}/projects/${encodeURIComponent(resolvedProjectId)}/context-pack`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ task })
        });

        if (!response.ok) {
          const detail = await response.text();
          return {
            ok: false,
            error: `AKDB context pack failed (${response.status}).`,
            diagnostics: [connectorDiagnostic(detail || `AKDB context pack failed (${response.status}).`)]
          };
        }

        const data = await readJsonResponse<Record<string, unknown>>(response);
        return {
          ok: true,
          data,
          provenance: {
            connector: "akdb",
            source: "context-pack",
            projectId: resolvedProjectId,
            fetchedAt: new Date().toISOString()
          }
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "AKDB context pack request failed.";
        return {
          ok: false,
          error: message,
          diagnostics: [connectorDiagnostic(message)]
        };
      }
    },

    async listNormativeDiagrams(projectId, filter) {
      const resolvedProjectId = resolveProjectId(context, projectId);
      const params = new URLSearchParams();
      if (filter?.kind) {
        params.set("kind", filter.kind);
      }
      if (filter?.limit) {
        params.set("limit", String(filter.limit));
      }
      const queryString = params.toString();
      const url = `${baseUrl}/projects/${encodeURIComponent(resolvedProjectId)}/uml/diagrams${queryString ? `?${queryString}` : ""}`;

      try {
        const response = await resolveFetch(context)(url);
        if (!response.ok) {
          const detail = await response.text();
          return {
            ok: false,
            error: `AKDB diagram listing failed (${response.status}).`,
            diagnostics: [connectorDiagnostic(detail || `AKDB diagram listing failed (${response.status}).`)]
          };
        }

        const payload = await readJsonResponse<Array<Record<string, unknown>>>(response);
        const diagrams = payload.map(normalizeDiagram).filter((diagram) => diagram.diagramId && matchesQuery(diagram, filter?.query));
        return {
          ok: true,
          data: diagrams,
          provenance: {
            connector: "akdb",
            source: "uml/diagrams",
            projectId: resolvedProjectId,
            fetchedAt: new Date().toISOString()
          }
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "AKDB diagram listing request failed.";
        return {
          ok: false,
          error: message,
          diagnostics: [connectorDiagnostic(message)]
        };
      }
    },

    async fetchDiagramSource(diagramId, projectId) {
      const resolvedProjectId = resolveProjectId(context, projectId);
      const normalizedDiagramId = diagramId.trim();
      if (!normalizedDiagramId) {
        return {
          ok: false,
          error: "Diagram id is required.",
          diagnostics: [connectorDiagnostic("AKDB diagram id is required.", "connector.akdb.diagram_required")]
        };
      }

      try {
        const response = await resolveFetch(context)(
          `${baseUrl}/projects/${encodeURIComponent(resolvedProjectId)}/uml/diagrams/${encodeURIComponent(normalizedDiagramId)}`
        );
        if (!response.ok) {
          const detail = await response.text();
          return {
            ok: false,
            error: `AKDB diagram fetch failed (${response.status}).`,
            diagnostics: [connectorDiagnostic(detail || `AKDB diagram fetch failed (${response.status}).`)]
          };
        }

        const payload = await readJsonResponse<Record<string, unknown>>(response);
        const source = resolveSource(payload);
        if (!source.trim()) {
          return {
            ok: false,
            error: "AKDB diagram response did not include source text.",
            diagnostics: [connectorDiagnostic("AKDB diagram response did not include source text.", "connector.akdb.source_missing")]
          };
        }

        const data: AkdbDiagramSource = {
          diagramId: normalizedDiagramId,
          source,
          notation: resolveNotation(payload),
          title: typeof payload.title === "string" ? payload.title : undefined,
          sourceUri: typeof payload.source_uri === "string" ? payload.source_uri : undefined,
          sourceKey: typeof payload.source_key === "string" ? payload.source_key : undefined
        };

        return {
          ok: true,
          data,
          provenance: {
            connector: "akdb",
            source: "uml/diagram",
            projectId: resolvedProjectId,
            diagramId: normalizedDiagramId,
            sourceUri: data.sourceUri,
            sourceKey: data.sourceKey,
            fetchedAt: new Date().toISOString()
          }
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "AKDB diagram fetch request failed.";
        return {
          ok: false,
          error: message,
          diagnostics: [connectorDiagnostic(message)]
        };
      }
    },

    async exportAndStage(plantUmlSource, targetPath, provenance) {
      const normalizedTarget = targetPath.trim().replace(/\\/g, "/");
      if (!normalizedTarget) {
        return {
          ok: false,
          error: "Target path is required.",
          diagnostics: [connectorDiagnostic("Export target path is required.", "connector.akdb.target_required")]
        };
      }
      if (!plantUmlSource.trim()) {
        return {
          ok: false,
          error: "PlantUML source is required.",
          diagnostics: [connectorDiagnostic("PlantUML source is required.", "connector.akdb.source_required")]
        };
      }

      const exportRoot = path.resolve(context.exportRoot);
      const resolvedTarget = path.resolve(exportRoot, normalizedTarget);
      if (resolvedTarget !== exportRoot && !resolvedTarget.startsWith(`${exportRoot}${path.sep}`)) {
        return {
          ok: false,
          error: "Export target escapes configured export root.",
          diagnostics: [connectorDiagnostic("Export target escapes configured export root.", "connector.akdb.target_escape")]
        };
      }

      try {
        await mkdir(path.dirname(resolvedTarget), { recursive: true });
        await writeFile(resolvedTarget, plantUmlSource.endsWith("\n") ? plantUmlSource : `${plantUmlSource}\n`, "utf8");

        const provenancePath = `${resolvedTarget}.provenance.json`;
        const provenancePayload = {
          ...provenance,
          stagedAt: new Date().toISOString(),
          targetPath: normalizedTarget
        };
        await writeFile(provenancePath, `${JSON.stringify(provenancePayload, null, 2)}\n`, "utf8");

        return {
          ok: true,
          data: {
            targetPath: normalizedTarget,
            provenancePath: path.relative(exportRoot, provenancePath).replace(/\\/g, "/"),
            bytesWritten: Buffer.byteLength(plantUmlSource, "utf8")
          },
          provenance: provenancePayload
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to stage PlantUML export.";
        return {
          ok: false,
          error: message,
          diagnostics: [connectorDiagnostic(message)]
        };
      }
    }
  };
}
