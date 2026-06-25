import type { TrackShape } from "../model/shape";
import { isTauri } from "./traceClient";

export type UnrealApplyRequest = {
  shape: TrackShape;
  actorName?: string;
  host?: string;
  port?: number;
  replace?: boolean;
  createRoadMesh?: boolean;
  meshPieceLengthM?: number;
  dryRun?: boolean;
};

export type UnrealApplyResult = {
  ok?: boolean;
  actor?: string;
  point_count?: number;
  scaled_length_m?: number;
  estimated_mesh_piece_count?: number;
  mesh_piece_count?: number | null;
  layout_count?: number;
  layouts?: Array<{
    layout_id?: string;
    kind?: string;
    point_count?: number;
    scaled_length_m?: number;
    estimated_mesh_piece_count?: number;
  }>;
  warnings?: Array<{ code?: string; message?: string; severity?: string }>;
  error?: string;
};

export interface UnrealApplyClient {
  apply(req: UnrealApplyRequest): Promise<UnrealApplyResult>;
}

function toPayload(req: UnrealApplyRequest) {
  return {
    shape: req.shape,
    actor_name: req.actorName,
    host: req.host,
    port: req.port,
    replace: req.replace,
    create_road_mesh: req.createRoadMesh,
    mesh_piece_length_m: req.meshPieceLengthM,
    dry_run: req.dryRun,
  };
}

export function httpUnrealApplyClient(fetchImpl: typeof fetch = fetch): UnrealApplyClient {
  return {
    async apply(req) {
      const resp = await fetchImpl("/api/apply-unreal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(req)),
      });
      const data = (await resp.json()) as UnrealApplyResult;
      if (!resp.ok && !data.error) return { error: `HTTP ${resp.status}` };
      return data;
    },
  };
}

type TauriGlobal = {
  core: { invoke: (cmd: string, args?: unknown) => Promise<unknown> };
};

export function tauriUnrealApplyClient(): UnrealApplyClient {
  return {
    async apply(req) {
      try {
        const tauri = (window as unknown as { __TAURI__: TauriGlobal }).__TAURI__;
        return (await tauri.core.invoke("apply_to_unreal", { request: toPayload(req) })) as UnrealApplyResult;
      } catch (e) {
        return { error: e instanceof Error ? e.message : String(e) };
      }
    },
  };
}

export function getUnrealApplyClient(): UnrealApplyClient {
  return isTauri() ? tauriUnrealApplyClient() : httpUnrealApplyClient();
}
