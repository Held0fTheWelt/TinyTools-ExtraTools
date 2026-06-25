import { useRef } from "react";
import type { CommandStack } from "../state/commands";
import type { TrackShape } from "../model/shape";
import { deserializeShape, serializeShape } from "../io/file";

export function Toolbar({
  stack,
  fileName,
  onOpen,
  onFileNameChange,
  onImportImage,
  onApplyUnreal,
  applyBusy = false,
}: {
  stack: CommandStack<TrackShape>;
  fileName: string;
  onOpen: (doc: TrackShape) => void;
  onFileNameChange: (name: string) => void;
  onImportImage: () => void;
  onApplyUnreal?: () => void;
  applyBusy?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleOpen = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      onOpen(deserializeShape(reader.result as string));
      onFileNameChange(file.name);
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const handleSave = () => {
    const blob = new Blob([serializeShape(stack.state)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      data-testid="toolbar"
      style={{ display: "flex", flexWrap: "wrap", gap: 8, padding: 8, borderBottom: "1px solid #ccc" }}
    >
      <input ref={inputRef} type="file" accept=".json" style={{ display: "none" }} onChange={handleOpen} />
      <button type="button" onClick={() => inputRef.current?.click()}>
        Open
      </button>
      <button type="button" onClick={onImportImage}>
        Load image...
      </button>
      <button type="button" onClick={onApplyUnreal} disabled={applyBusy || !onApplyUnreal}>
        {applyBusy ? "Sending..." : "Send to Unreal"}
      </button>
      <button type="button" onClick={handleSave}>
        Save
      </button>
      <button type="button" disabled={!stack.canUndo} onClick={() => stack.undo()}>
        Undo
      </button>
      <button type="button" disabled={!stack.canRedo} onClick={() => stack.redo()}>
        Redo
      </button>
    </div>
  );
}
