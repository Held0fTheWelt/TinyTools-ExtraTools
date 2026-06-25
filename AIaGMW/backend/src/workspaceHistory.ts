import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import type { WorkspaceHistoryStatus } from "@aiagmw/shared";

interface Snapshot {
  files: Map<string, string>;
}

interface HistoryEntry {
  label: string;
  before: Snapshot;
  after: Snapshot;
}

const trackedEntries = [".umlworkspace/workspace.json", "models", "diagrams", "layouts", "proposals", "history"];

export class WorkspaceHistory {
  private readonly undoStack: HistoryEntry[] = [];
  private readonly redoStack: HistoryEntry[] = [];
  private root: string;

  constructor(
    root: string,
    private readonly maxEntries = 30
  ) {
    this.root = root;
  }

  setRoot(root: string) {
    this.root = root;
    this.undoStack.length = 0;
    this.redoStack.length = 0;
  }

  status(): WorkspaceHistoryStatus {
    return {
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
      nextUndoLabel: this.undoStack.at(-1)?.label,
      nextRedoLabel: this.redoStack.at(-1)?.label
    };
  }

  async record<T>(label: string, action: () => Promise<T>): Promise<T> {
    const before = await captureSnapshot(this.root);
    const result = await action();
    const after = await captureSnapshot(this.root);

    if (!snapshotsEqual(before, after)) {
      this.undoStack.push({ label, before, after });
      if (this.undoStack.length > this.maxEntries) {
        this.undoStack.shift();
      }
      this.redoStack.length = 0;
    }

    return result;
  }

  async undo(): Promise<WorkspaceHistoryStatus> {
    const entry = this.undoStack.pop();
    if (!entry) {
      return this.status();
    }

    await restoreSnapshot(this.root, entry.before);
    this.redoStack.push(entry);
    return this.status();
  }

  async redo(): Promise<WorkspaceHistoryStatus> {
    const entry = this.redoStack.pop();
    if (!entry) {
      return this.status();
    }

    await restoreSnapshot(this.root, entry.after);
    this.undoStack.push(entry);
    return this.status();
  }
}

async function captureSnapshot(root: string): Promise<Snapshot> {
  const files = new Map<string, string>();
  for (const entry of trackedEntries) {
    const absolute = safeResolve(root, entry);
    const found = await listTrackedFiles(root, absolute);
    for (const file of found) {
      files.set(toRelative(root, file), await readFile(file, "utf8"));
    }
  }
  return { files };
}

async function restoreSnapshot(root: string, snapshot: Snapshot): Promise<void> {
  const currentFiles = new Set<string>();
  for (const entry of trackedEntries) {
    const absolute = safeResolve(root, entry);
    const found = await listTrackedFiles(root, absolute);
    for (const file of found) {
      currentFiles.add(toRelative(root, file));
    }
  }

  for (const relativePath of currentFiles) {
    if (!snapshot.files.has(relativePath)) {
      await rm(safeResolve(root, relativePath), { force: true });
    }
  }

  for (const [relativePath, contents] of snapshot.files.entries()) {
    const file = safeResolve(root, relativePath);
    await mkdir(path.dirname(file), { recursive: true });
    await writeFile(file, contents, "utf8");
  }
}

async function listTrackedFiles(root: string, absolute: string): Promise<string[]> {
  try {
    const statEntries = await readdir(absolute, { withFileTypes: true });
    const nested = await Promise.all(
      statEntries.map(async (entry) => {
        const entryPath = path.join(absolute, entry.name);
        const relativePath = toRelative(root, entryPath);
        if (relativePath.startsWith(".umlworkspace/cache")) {
          return [];
        }
        if (entry.isDirectory()) {
          return listTrackedFiles(root, entryPath);
        }
        return entry.isFile() ? [entryPath] : [];
      })
    );
    return nested.flat().sort();
  } catch {
    try {
      await readFile(absolute, "utf8");
      return [absolute];
    } catch {
      return [];
    }
  }
}

function snapshotsEqual(left: Snapshot, right: Snapshot): boolean {
  if (left.files.size !== right.files.size) {
    return false;
  }

  for (const [file, contents] of left.files.entries()) {
    if (right.files.get(file) !== contents) {
      return false;
    }
  }

  return true;
}

function safeResolve(root: string, relativePath: string): string {
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(resolvedRoot, relativePath);
  if (resolved !== resolvedRoot && !resolved.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error(`Path escapes workspace root: ${resolved}`);
  }
  return resolved;
}

function toRelative(root: string, file: string): string {
  return path.relative(root, file).replaceAll(path.sep, "/");
}
