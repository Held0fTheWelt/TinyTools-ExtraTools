import { z } from "zod";

const Vec = z.object({
  x: z.number().finite(),
  y: z.number().finite(),
  z: z.number().finite().optional(),
});

const Anchor = z
  .object({
    id: z.string().regex(/^[a-z0-9_]+$/),
    label: z.string().optional(),
    x: z.number().finite(),
    y: z.number().finite(),
    z: z.number().finite().optional(),
    tags: z.array(z.string()).optional(),
  })
  .strict();

const Base = {
  id: z.string(),
  label: z.string().optional(),
  from: z.string(),
  to: z.string(),
  samples: z.number().int().positive().optional(),
};

const LineSeg = z.object({ ...Base, type: z.literal("line") }).strict();
const BezierSeg = z
  .object({
    ...Base,
    type: z.literal("bezier"),
    handle_from: Vec,
    handle_to: Vec,
    adaptive: z.boolean().optional(),
  })
  .strict();

const Segment = z.discriminatedUnion("type", [LineSeg, BezierSeg]);

const LayoutKind = z.enum(["pit_lane", "alternate", "service_road", "decorative"]);

const Units = z
  .object({
    source_unit: z.string(),
    unreal_unit: z.string(),
    scale_to_target_length: z.boolean(),
    scale_mode: z.enum(["none", "uniform_xy", "uniform_xyz"]),
    target_length_m: z.number().finite().nullable().optional(),
  })
  .strict()
  .refine(
    (u) => !u.scale_to_target_length || (u.target_length_m != null && u.target_length_m > 0),
    { message: "target_length_m required and > 0 when scale_to_target_length is true" },
  );

export const TrackShapeSchema = z
  .object({
    schema: z.literal("track_shape.v1"),
    name: z.string(),
    closed: z.boolean(),
    units: Units,
    sampling: z.object({}).passthrough(),
    mesh: z.object({}).passthrough(),
    tangents: z.object({}).passthrough().optional(),
    anchors: z.array(Anchor),
    segments: z.array(Segment),
    layouts: z
      .array(
        z
          .object({
            id: z.string().regex(/^[A-Za-z][A-Za-z0-9_-]*$/),
            label: z.string().optional(),
            kind: LayoutKind,
            enabled: z.boolean().optional(),
            closed: z.boolean(),
            anchors: z.array(Anchor),
            segments: z.array(Segment),
            metadata: z.object({}).passthrough().optional(),
          })
          .strict(),
      )
      .optional(),
    metadata: z.object({}).passthrough().optional(),
  })
  .strict();

export type TrackShape = z.infer<typeof TrackShapeSchema>;
export type TrackShapeLayout = NonNullable<TrackShape["layouts"]>[number];

export function parseTrackShape(raw: unknown): TrackShape {
  return TrackShapeSchema.parse(raw);
}
