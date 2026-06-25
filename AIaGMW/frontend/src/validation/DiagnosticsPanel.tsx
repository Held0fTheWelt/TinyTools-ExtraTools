import type { Diagnostic } from "@aiagmw/shared";

interface DiagnosticsPanelProps {
  diagnostics: Diagnostic[];
  onNavigate?: (targetId: string) => void;
}

export function DiagnosticsPanel({ diagnostics, onNavigate }: DiagnosticsPanelProps) {
  if (diagnostics.length === 0) {
    return <div className="diagnostics-empty">No diagnostics.</div>;
  }

  return (
    <div className="diagnostics-list">
      {diagnostics.slice(0, 8).map((diagnostic, index) => (
        <div
          key={`${diagnostic.code}-${index}`}
          className={`diagnostic ${diagnostic.level}${diagnostic.targetId && onNavigate ? " clickable" : ""}`}
          onClick={() => {
            if (diagnostic.targetId && onNavigate) {
              onNavigate(diagnostic.targetId);
            }
          }}
          onKeyDown={(event) => {
            if (diagnostic.targetId && onNavigate && (event.key === "Enter" || event.key === " ")) {
              event.preventDefault();
              onNavigate(diagnostic.targetId);
            }
          }}
          role={diagnostic.targetId && onNavigate ? "button" : undefined}
          tabIndex={diagnostic.targetId && onNavigate ? 0 : undefined}
        >
          <strong>{diagnostic.level}</strong>
          <span>{diagnostic.message}</span>
          {diagnostic.file ? <code>{diagnostic.file}</code> : null}
        </div>
      ))}
    </div>
  );
}
