export interface PrefStore {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

const KEY = "projectFolder";

export const loadProjectFolder = (store: PrefStore) => store.get(KEY);
export const saveProjectFolder = (store: PrefStore, path: string) => store.set(KEY, path);
