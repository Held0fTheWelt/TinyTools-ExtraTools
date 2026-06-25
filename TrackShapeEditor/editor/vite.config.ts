import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import type { IncomingMessage, ServerResponse } from "node:http";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

// npm runs scripts with cwd = this package dir (track-shape-editor).
// The Python toolchain lives next to the editor at ../../TrackShape.
const trackShapeDir = resolve(process.cwd(), "../../TrackShape");
// Pass the script RELATIVE to cwd, not as an absolute path: when a WSL-hosted
// Vite spawns the Windows python.exe, an absolute "/mnt/d/…" arg gets mis-read
// as "D:\mnt\d\…". A relative name resolves against the (interop-translated)
// cwd correctly in both WSL and native Windows.
const traceScriptName = "trace_for_editor.py";
const applyScriptName = "apply_for_editor.py";

function resolvePython(): string {
  const candidates = [
    process.env.TRACK_SHAPE_PYTHON,
    resolve(trackShapeDir, ".venv/Scripts/python.exe"), // Windows venv
    resolve(trackShapeDir, ".venv/bin/python"), // POSIX venv
  ].filter(Boolean) as string[];
  for (const c of candidates) if (existsSync(c)) return c;
  return process.platform === "win32" ? "python" : "python3";
}

function sendJson(res: ServerResponse, code: number, obj: unknown): void {
  const body = JSON.stringify(obj);
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.end(body);
}

function readRequestBody(req: IncomingMessage, cb: (body: Buffer) => void): void {
  const chunks: Buffer[] = [];
  req.on("data", (c: Buffer) => chunks.push(c));
  req.on("end", () => cb(Buffer.concat(chunks)));
}

function runPythonJson(scriptName: string, body: Buffer, res: ServerResponse, label: string): void {
  const py = resolvePython();
  const child = spawn(py, [scriptName], { cwd: trackShapeDir });
  let out = "";
  let err = "";
  child.stdout.on("data", (d) => (out += d));
  child.stderr.on("data", (d) => (err += d));
  child.on("error", (e) =>
    sendJson(res, 500, { error: `Python could not be started (${py}): ${e.message}` }),
  );
  child.on("close", (code) => {
    let parsed: { error?: string } | undefined;
    try {
      parsed = JSON.parse(out);
    } catch {
      sendJson(res, 500, {
        error: `${label}-Ausgabe unlesbar (exit ${code}): ${(err || out).slice(0, 500)}`,
      });
      return;
    }
    sendJson(res, parsed?.error ? 422 : 200, parsed);
  });
  child.stdin.write(body);
  child.stdin.end();
}

    // Handle the editor's "Load image..." by spawning the Python tracer once per
// request and relaying its stdout. Using a subprocess (not a TCP server) is
// what lets a WSL-hosted editor drive a Windows Python venv: process interop
// works across that boundary, a localhost socket does not. apply:"serve" keeps
// this out of `vite build` and vitest entirely.
function pythonBridge(): Plugin {
  return {
    name: "track-shape-python-bridge",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/api/trace", (req, res, next) => {
        if (req.method !== "POST") return next();
        readRequestBody(req, (body) => runPythonJson(traceScriptName, body, res, "Tracer"));
      });
      server.middlewares.use("/api/apply-unreal", (req, res, next) => {
        if (req.method !== "POST") return next();
        readRequestBody(req, (body) => runPythonJson(applyScriptName, body, res, "Unreal-Apply"));
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), pythonBridge()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
  },
});
