import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import path from "node:path";

export interface TransactionWrite {
  file: string;
  data: unknown;
}

export async function runTransaction(writes: TransactionWrite[]): Promise<void> {
  const backups = new Map<string, string | null>();

  try {
    for (const { file, data } of writes) {
      try {
        backups.set(file, await readFile(file, "utf8"));
      } catch {
        backups.set(file, null);
      }
      await writeJson(file, data);
    }
  } catch (error) {
    for (const [file, content] of backups) {
      if (content === null) {
        await unlink(file).catch(() => undefined);
      } else {
        await writeFile(file, content, "utf8");
      }
    }
    throw error;
  }
}

async function writeJson(file: string, value: unknown): Promise<void> {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}
