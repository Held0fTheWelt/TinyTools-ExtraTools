export interface OpenedFile {
  name: string;
  text: string;
}

export interface FileBackend {
  open(): Promise<OpenedFile | null>;
  save(name: string, text: string): Promise<void>;
}

export interface TauriFsApi {
  openDialog: () => Promise<string | null>;
  readText: (path: string) => Promise<string>;
  saveDialog: (suggestedName: string) => Promise<string | null>;
  writeText: (path: string, text: string) => Promise<void>;
}

export function makeTauriBackend(api: TauriFsApi): FileBackend {
  return {
    async open() {
      const path = await api.openDialog();
      if (!path) return null;
      return { name: path, text: await api.readText(path) };
    },
    async save(name, text) {
      const path = await api.saveDialog(name);
      if (path) await api.writeText(path, text);
    },
  };
}
