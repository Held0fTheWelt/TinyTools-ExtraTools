import path from "node:path";

export function sanitizeFileName(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "_");
}

export function safeJoin(root: string, ...segments: string[]): string {
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(resolvedRoot, ...segments);
  if (resolved !== resolvedRoot && !resolved.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error(`Path escapes workspace root: ${resolved}`);
  }
  return resolved;
}

export function relativePath(root: string, file: string): string {
  return path.relative(root, file).replaceAll(path.sep, "/");
}
