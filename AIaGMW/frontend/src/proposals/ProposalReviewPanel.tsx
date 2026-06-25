import { Check, Eye, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { PatchPreviewResponse, ProposalSummary } from "@aiagmw/shared";
import { applyProposal, approveProposal, previewProposal, rejectProposal } from "../api";

interface ProposalReviewPanelProps {
  proposals: ProposalSummary[];
  selectedProposalId: string | null;
  onSelectProposal: (proposalId: string | null) => void;
  onChanged: () => Promise<void>;
  onPreviewDiff: (preview: PatchPreviewResponse | null) => void;
}

export function ProposalReviewPanel({
  proposals,
  selectedProposalId,
  onSelectProposal,
  onChanged,
  onPreviewDiff
}: ProposalReviewPanelProps) {
  const [preview, setPreview] = useState<PatchPreviewResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = proposals.find((proposal) => proposal.id === selectedProposalId) ?? null;

  useEffect(() => {
    if (!selectedProposalId) {
      setPreview(null);
      onPreviewDiff(null);
      return;
    }

    let cancelled = false;
    setBusy(true);
    setError(null);
    previewProposal(selectedProposalId)
      .then((result) => {
        if (!cancelled) {
          setPreview(result);
          onPreviewDiff(result);
        }
      })
      .catch((previewError) => {
        if (!cancelled) {
          setError(previewError instanceof Error ? previewError.message : "Could not preview proposal.");
          setPreview(null);
          onPreviewDiff(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setBusy(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProposalId, onPreviewDiff]);

  async function handleApprove() {
    if (!selectedProposalId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await approveProposal(selectedProposalId, {
        approvedBy: "user",
        approvalNote: "Approved from proposal review panel",
        validationStatus: preview?.applicable ? "passed" : "failed"
      });
      await onChanged();
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : "Could not approve proposal.");
    } finally {
      setBusy(false);
    }
  }

  async function handleApply() {
    if (!selectedProposalId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await applyProposal(selectedProposalId, "user");
      onSelectProposal(null);
      await onChanged();
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "Could not apply proposal.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    if (!selectedProposalId) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await rejectProposal(selectedProposalId);
      onSelectProposal(null);
      await onChanged();
    } catch (rejectError) {
      setError(rejectError instanceof Error ? rejectError.message : "Could not reject proposal.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="proposal-review">
      <div className="proposal-list">
        {proposals.map((proposal) => (
          <button
            key={proposal.id}
            type="button"
            className={proposal.id === selectedProposalId ? "proposal-chip active" : "proposal-chip"}
            onClick={() => onSelectProposal(proposal.id)}
          >
            <strong>{proposal.title}</strong>
            <span>{proposal.status}</span>
            <span>{proposal.operationCount} ops</span>
          </button>
        ))}
        {proposals.length === 0 ? <span className="muted">No proposals</span> : null}
      </div>

      {selected ? (
        <div className="proposal-detail">
          <header>
            <h3>{selected.title}</h3>
            <span className={`risk-badge risk-${selected.risk ?? "low"}`}>{selected.risk ?? "low"} risk</span>
          </header>

          {preview ? (
            <>
              <p className="proposal-intent">{preview.proposal.intent}</p>
              {preview.proposal.reasoningSummary ? <p className="muted">{preview.proposal.reasoningSummary}</p> : null}

              <div className="proposal-meta">
                <span>Applicable: {preview.applicable ? "yes" : "no"}</span>
                <span>Models: {preview.diff.affectedModelIds.join(", ") || "none"}</span>
                <span>Diagrams: {preview.diff.affectedDiagramIds.join(", ") || "none"}</span>
              </div>

              <details open>
                <summary>Operations ({preview.proposal.operations.length})</summary>
                <ul className="operation-list">
                  {preview.proposal.operations.map((operation, index) => (
                    <li key={`${operation.op}-${index}`}>
                      <code>{operation.op}</code>
                      {operation.modelId ? <span> model {operation.modelId}</span> : null}
                      {operation.diagramId ? <span> diagram {operation.diagramId}</span> : null}
                      {operation.elementId ? <span> element {operation.elementId}</span> : null}
                    </li>
                  ))}
                </ul>
              </details>

              <details>
                <summary>Diff summary</summary>
                <ul className="diff-summary">
                  <li>+{preview.diff.addedElements.length} elements</li>
                  <li>-{preview.diff.removedElements.length} elements</li>
                  <li>~{preview.diff.updatedElements.length} element updates</li>
                  <li>+{preview.diff.addedRelations.length} relations</li>
                  <li>{preview.diff.layoutChanges.length} layout changes</li>
                </ul>
              </details>

              {preview.diagnostics.length > 0 ? (
                <details open>
                  <summary>Validation ({preview.diagnostics.length})</summary>
                  <ul className="proposal-diagnostics">
                    {preview.diagnostics.slice(0, 12).map((diagnostic, index) => (
                      <li key={`${diagnostic.code}-${index}`} className={`diag-${diagnostic.level}`}>
                        {diagnostic.message}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </>
          ) : null}

          {error ? <p className="proposal-error">{error}</p> : null}

          <div className="proposal-actions">
            <button type="button" className="secondary-action" disabled={busy || !preview} onClick={() => void handleApprove()}>
              <Check size={14} aria-hidden />
              Approve
            </button>
            <button type="button" disabled={busy || !preview?.applicable} onClick={() => void handleApply()}>
              <Eye size={14} aria-hidden />
              Apply
            </button>
            <button type="button" className="danger-action" disabled={busy} onClick={() => void handleReject()}>
              <X size={14} aria-hidden />
              Reject
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
