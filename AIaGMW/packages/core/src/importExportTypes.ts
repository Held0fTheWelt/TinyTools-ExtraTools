export type DiagramImportFormat = "plantuml" | "mermaid";
export type DiagramExportFormat = "plantuml" | "mermaid";

export interface DiagramImportRequest {
  format: DiagramImportFormat;
  source: string;
  name?: string;
  sourcePath?: string;
}

export interface DiagramImportResult {
  model: import("@aiagmw/shared").UmlModel;
  diagram: import("@aiagmw/shared").UmlDiagram;
  layout: import("@aiagmw/shared").UmlLayout;
  sourcePath: string;
  imported: {
    elements: number;
    relations: number;
  };
}

export interface DiagramExportResult {
  format: DiagramExportFormat;
  diagramId: string;
  path: string;
  source: string;
}
