import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { loadWorkspace, type LoadWorkspaceOptions } from "./workspace";
import { safeJoin, sanitizeFileName } from "./workspacePaths";

export async function exportDiagramImage(
  options: LoadWorkspaceOptions,
  diagramId: string,
  format: "svg" | "png",
  content: string
): Promise<{ diagramId: string; format: "svg" | "png"; path: string }> {
  const state = await loadWorkspace(options);
  const diagram = state.diagrams.find((entry) => entry.data.id === diagramId);
  if (!diagram) {
    throw new Error(`Diagram ${diagramId} was not found.`);
  }

  const exportsDir = state.manifest?.paths.exports ?? "exports";
  const extension = format === "svg" ? "svg" : "png";
  const relative = path.join(exportsDir, `${sanitizeFileName(diagramId)}.${extension}`);
  const file = safeJoin(state.root, relative);
  await mkdir(path.dirname(file), { recursive: true });

  if (format === "svg") {
    await writeFile(file, content, "utf8");
  } else {
    const base64 = content.includes(",") ? content.split(",")[1] ?? content : content;
    await writeFile(file, Buffer.from(base64, "base64"));
  }

  return { diagramId, format, path: relative.replace(/\\/g, "/") };
}
