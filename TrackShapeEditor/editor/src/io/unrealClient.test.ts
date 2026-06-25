import { expect, test, vi } from "vitest";
import { httpUnrealApplyClient } from "./unrealClient";
import { parseTrackShape } from "../model/shape";
import example from "../../test/fixtures/daytona_shape.example.json";

test("posts the current shape to the Unreal apply endpoint", async () => {
  const fetchImpl = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ok: true, actor: "Track", point_count: 7 }),
  });
  const shape = parseTrackShape(example);

  const result = await httpUnrealApplyClient(fetchImpl as unknown as typeof fetch).apply({
    shape,
    actorName: "Track",
    host: "127.0.0.1",
    port: 8732,
    replace: true,
    createRoadMesh: true,
    meshPieceLengthM: 20,
  });

  expect(result.actor).toBe("Track");
  expect(fetchImpl).toHaveBeenCalledWith(
    "/api/apply-unreal",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"actor_name":"Track"'),
    }),
  );
  const body = JSON.parse(fetchImpl.mock.calls[0][1].body as string);
  expect(body).toMatchObject({
    actor_name: "Track",
    host: "127.0.0.1",
    port: 8732,
    replace: true,
    create_road_mesh: true,
    mesh_piece_length_m: 20,
  });
  expect(body.shape.schema).toBe("track_shape.v1");
});
