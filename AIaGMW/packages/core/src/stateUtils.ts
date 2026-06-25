import type { WorkspaceIndex } from "@aiagmw/shared";
import type { WorkspaceState } from "./workspace";

export function cloneWorkspaceState(state: WorkspaceState): WorkspaceState {
  return structuredClone(state);
}

export function rebuildWorkspaceIndex(state: WorkspaceState, index: WorkspaceIndex): void {
  state.index = index;
}
