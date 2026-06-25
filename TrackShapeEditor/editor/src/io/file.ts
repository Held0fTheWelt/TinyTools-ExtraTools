import { parseTrackShape, type TrackShape } from "../model/shape";

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as object)
        .sort()
        .map((k) => [k, sortKeys((value as Record<string, unknown>)[k])]),
    );
  }
  return value;
}

export function serializeShape(doc: TrackShape): string {
  return JSON.stringify(sortKeys(doc), null, 2) + "\n";
}

export function deserializeShape(text: string): TrackShape {
  return parseTrackShape(JSON.parse(text));
}
