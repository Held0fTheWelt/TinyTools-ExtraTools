from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fy_platform.ai.evidence_registry.compare_runs import build_compare_runs_delta
from fy_platform.ai.persistence_state import ensure_schema_state, record_migration_event
from fy_platform.ai.policy.review_policy import validate_transition
from fy_platform.ai.schemas.common import ArtifactRecord, CompareRunsDelta, EvidenceRecord, SuiteRunRecord, to_jsonable
from fy_platform.ai.workspace import ensure_workspace_layout, utc_now, workspace_root


class EvidenceRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root)
        ensure_workspace_layout(self.root)
        self.db_path = self.root / ".fydata" / "registry" / "registry.db"
        self._init_db()
        ensure_schema_state(self.root)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS suite_runs (
                    run_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    workspace_root TEXT NOT NULL,
                    target_repo_root TEXT,
                    target_repo_id TEXT,
                    status TEXT NOT NULL,
                    strategy_profile TEXT DEFAULT '',
                    run_metadata_json TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    role TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT,
                    FOREIGN KEY(run_id) REFERENCES suite_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    ownership_zone TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    deterministic INTEGER NOT NULL,
                    review_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    excerpt TEXT DEFAULT '',
                    FOREIGN KEY(run_id) REFERENCES suite_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS links (
                    src_id TEXT NOT NULL,
                    dst_id TEXT NOT NULL,
                    relation TEXT NOT NULL
                );
                """
            )
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(suite_runs)").fetchall()}
            if "strategy_profile" not in cols:
                conn.execute("ALTER TABLE suite_runs ADD COLUMN strategy_profile TEXT DEFAULT ''")
                record_migration_event(self.root, component="registry", from_version=2, to_version=3, action="add_strategy_profile_column")
            if "run_metadata_json" not in cols:
                conn.execute("ALTER TABLE suite_runs ADD COLUMN run_metadata_json TEXT DEFAULT '{}'")
                record_migration_event(self.root, component="registry", from_version=2, to_version=3, action="add_run_metadata_column")
            conn.commit()
        finally:
            conn.close()

    def start_run(self, *, suite: str, mode: str, target_repo_root: str | None, target_repo_id: str | None, strategy_profile: str = "", run_metadata: dict[str, Any] | None = None) -> SuiteRunRecord:
        rec = SuiteRunRecord(
            run_id=f"{suite}-{uuid.uuid4().hex[:12]}",
            suite=suite,
            mode=mode,
            started_at=utc_now(),
            ended_at=None,
            workspace_root=str(self.root),
            target_repo_root=target_repo_root,
            target_repo_id=target_repo_id,
            status="running",
            strategy_profile=strategy_profile,
            run_metadata=dict(run_metadata or {}),
        )
        self._execute(
            "INSERT INTO suite_runs(run_id, suite, mode, started_at, ended_at, workspace_root, target_repo_root, target_repo_id, status, strategy_profile, run_metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rec.run_id, rec.suite, rec.mode, rec.started_at, rec.ended_at, rec.workspace_root, rec.target_repo_root, rec.target_repo_id, rec.status, rec.strategy_profile, json.dumps(to_jsonable(rec.run_metadata))),
        )
        return rec

    def finish_run(self, run_id: str, *, status: str = "ok") -> None:
        self._execute("UPDATE suite_runs SET ended_at = ?, status = ? WHERE run_id = ?", (utc_now(), status, run_id))

    def record_artifact(self, *, suite: str, run_id: str, format: str, role: str, path: str, payload: Any | None = None) -> ArtifactRecord:
        rec = ArtifactRecord(artifact_id=uuid.uuid4().hex, suite=suite, run_id=run_id, format=format, role=role, path=path, created_at=utc_now())
        self._execute(
            "INSERT INTO artifacts(artifact_id, suite, run_id, format, role, path, created_at, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rec.artifact_id, rec.suite, rec.run_id, rec.format, rec.role, rec.path, rec.created_at, json.dumps(to_jsonable(payload)) if payload is not None else None),
        )
        return rec

    def record_evidence(self, *, suite: str, run_id: str, kind: str, source_uri: str, ownership_zone: str, content_hash: str, mime_type: str, deterministic: bool, review_state: str = "raw", excerpt: str = "") -> EvidenceRecord:
        rec = EvidenceRecord(uuid.uuid4().hex, suite, run_id, kind, source_uri, ownership_zone, content_hash, mime_type, deterministic, review_state, utc_now())
        self._execute(
            "INSERT INTO evidence(evidence_id, suite, run_id, kind, source_uri, ownership_zone, content_hash, mime_type, deterministic, review_state, created_at, excerpt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rec.evidence_id, rec.suite, rec.run_id, rec.kind, rec.source_uri, rec.ownership_zone, rec.content_hash, rec.mime_type, int(rec.deterministic), rec.review_state, rec.created_at, excerpt),
        )
        return rec

    def update_evidence_review_state(self, evidence_id: str, new_state: str) -> dict[str, Any]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT review_state FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return {"ok": False, "reason": "evidence_not_found", "evidence_id": evidence_id}
            current = row["review_state"]
            result = validate_transition(current, new_state)
            if not result.ok:
                return {"ok": False, "reason": result.reason, "evidence_id": evidence_id, "current_state": current, "new_state": new_state}
            conn.execute("UPDATE evidence SET review_state = ? WHERE evidence_id = ?", (new_state, evidence_id))
            conn.commit()
            return {"ok": True, "evidence_id": evidence_id, "current_state": current, "new_state": new_state}
        finally:
            conn.close()

    def list_evidence(self, suite: str | None = None, review_state: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM evidence WHERE 1=1"
        params: list[Any] = []
        if suite:
            query += " AND suite = ?"
            params.append(suite)
        if review_state:
            query += " AND review_state = ?"
            params.append(review_state)
        return self._fetch_all(query + " ORDER BY created_at DESC", params)

    def evidence_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM evidence WHERE run_id = ? ORDER BY created_at ASC", (run_id,))

    def link(self, src_id: str, dst_id: str, relation: str) -> None:
        self._execute("INSERT INTO links(src_id, dst_id, relation) VALUES (?, ?, ?)", (src_id, dst_id, relation))

    def latest_run(self, suite: str) -> dict[str, Any] | None:
        return self._decode_run_row(self._fetch_one("SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC LIMIT 1", (suite,)))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self._decode_run_row(self._fetch_one("SELECT * FROM suite_runs WHERE run_id = ?", (run_id,)))

    def list_runs(self, suite: str) -> list[dict[str, Any]]:
        return [item for item in (self._decode_run_row(row) for row in self._fetch_all("SELECT * FROM suite_runs WHERE suite = ? ORDER BY started_at DESC", (suite,))) if item]

    def artifacts_for_run(self, run_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("SELECT * FROM artifacts WHERE run_id = ? ORDER BY created_at ASC", (run_id,))

    def artifact_payload(self, artifact_id: str) -> Any | None:
        row = self._fetch_one("SELECT payload_json FROM artifacts WHERE artifact_id = ?", (artifact_id,))
        if not row or not row["payload_json"]:
            return None
        return json.loads(row["payload_json"])

    def compare_runs(self, left_run_id: str, right_run_id: str) -> CompareRunsDelta | None:
        return build_compare_runs_delta(self, left_run_id, right_run_id)

    def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        conn = self._connect()
        try:
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()

    def _fetch_one(self, query: str, params: tuple[Any, ...]):
        conn = self._connect()
        try:
            return conn.execute(query, params).fetchone()
        finally:
            conn.close()

    def _fetch_all(self, query: str, params) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            return [dict(row) for row in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    def _decode_run_row(self, row) -> dict[str, Any] | None:
        if not row:
            return None
        payload = dict(row)
        try:
            payload["run_metadata"] = json.loads(payload.get("run_metadata_json") or "{}")
        except json.JSONDecodeError:
            payload["run_metadata"] = {}
        return payload
