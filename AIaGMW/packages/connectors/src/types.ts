import type { Diagnostic } from "@aiagmw/shared";

export interface Provenance {
  connector: string;
  source: string;
  sourceUri?: string;
  sourceKey?: string;
  projectId?: string;
  diagramId?: string;
  fetchedAt: string;
  metadata?: Record<string, unknown>;
}

export interface ConnectorContext {
  akdbUrl: string;
  akdbProjectId: string;
  exportRoot: string;
  fetchImpl?: typeof fetch;
}

export interface ConnectorSettings {
  akdbUrl: string;
  akdbProjectId: string;
  akdbExportRoot: string;
  connectorsEnabled: string[];
}

export interface ConnectorResult<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
  diagnostics?: Diagnostic[];
  provenance?: Provenance;
}

export interface AkdbDiagramSummary {
  diagramId: string;
  title?: string;
  diagramKind?: string;
  sourceUri?: string;
  sourceKey?: string;
  notation?: string;
}

export interface AkdbDiagramSource {
  diagramId: string;
  source: string;
  notation: "plantuml" | "mermaid";
  title?: string;
  sourceUri?: string;
  sourceKey?: string;
}

export interface AkdbExportStageResult {
  targetPath: string;
  provenancePath: string;
  bytesWritten: number;
}

export interface ConnectorDescriptor {
  id: string;
  label: string;
  capabilities: string[];
}

export interface ConnectorStatusEntry {
  id: string;
  enabled: boolean;
  reachable?: boolean;
  error?: string;
}
