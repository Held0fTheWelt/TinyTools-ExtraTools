// Transport abstraction for the image tracer. The same React dialog drives
// either front door:
//   * Browser  -> POST /api/trace  (handled by the Vite dev middleware)
//   * Tauri    -> invoke("trace_image") (handled by the Rust command)
// Both ultimately run the same Python trace_for_editor.py and return the same
// { shape, report } | { error } shape.

export type TraceRequest = {
  image_b64: string;
  filename: string;
  target_length_m: number;
  origin?: "first-anchor" | "image" | "centroid";
  meters_per_pixel?: number;
  tolerance?: number;
  track_color?: string;
  background_color?: string;
  invert?: boolean;
  lines_only?: boolean;
  guide_points_px?: Array<{ x: number; y: number }>;
};

export type TraceResult = {
  shape?: unknown;
  report?: unknown;
  error?: string;
};

export interface TraceClient {
  trace(req: TraceRequest): Promise<TraceResult>;
}

// Browser: talk to the Vite dev-server middleware. A network failure (helper
// not running) rejects, which the dialog turns into a friendly message.
export function httpTraceClient(fetchImpl: typeof fetch = fetch): TraceClient {
  return {
    async trace(req) {
      const resp = await fetchImpl("/api/trace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      const data = (await resp.json()) as TraceResult;
      if (!resp.ok && !data.error) return { error: `HTTP ${resp.status}` };
      return data;
    },
  };
}

type TauriGlobal = {
  core: { invoke: (cmd: string, args?: unknown) => Promise<unknown> };
};

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

// Tauri: call the Rust `trace_image` command through the global bridge
// (withGlobalTauri = true), so no @tauri-apps/api package is needed.
export function tauriTraceClient(): TraceClient {
  return {
    async trace(req) {
      try {
        const tauri = (window as unknown as { __TAURI__: TauriGlobal }).__TAURI__;
        return (await tauri.core.invoke("trace_image", { request: req })) as TraceResult;
      } catch (e) {
        return { error: e instanceof Error ? e.message : String(e) };
      }
    },
  };
}

export function getTraceClient(): TraceClient {
  return isTauri() ? tauriTraceClient() : httpTraceClient();
}
