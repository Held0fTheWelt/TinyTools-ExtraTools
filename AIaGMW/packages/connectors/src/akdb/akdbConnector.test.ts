import { afterEach, describe, expect, it, vi } from "vitest";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { tmpdir } from "node:os";
import { createAkdbConnector } from "./akdbConnector";
import { getAkdbConnector, parseEnabledConnectors, probeConnectorStatus } from "../registry";
import type { ConnectorContext } from "../types";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" }
  });
}

describe("akdbConnector", () => {
  const fetchMock = vi.fn<typeof fetch>();
  const context: ConnectorContext = {
    akdbUrl: "http://127.0.0.1:8787",
    akdbProjectId: "tiny-tool-development",
    exportRoot: path.join(tmpdir(), "aiagmw-akdb-export"),
    fetchImpl: fetchMock
  };

  afterEach(() => {
    fetchMock.mockReset();
    delete process.env.AIAGMW_CONNECTORS_ENABLED;
  });

  it("fetchContextPack posts task to AKDB context-pack endpoint", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ accepted_adrs: [{ local_id: "ADR-0001" }] }));
    const connector = createAkdbConnector(context);

    const result = await connector.fetchContextPack("Update class model");

    expect(result.ok).toBe(true);
    expect(result.data?.accepted_adrs).toEqual([{ local_id: "ADR-0001" }]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8787/projects/tiny-tool-development/context-pack",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ task: "Update class model" })
      })
    );
  });

  it("listNormativeDiagrams maps AKDB diagram rows", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse([
        {
          diagram_id: "model",
          title: "Core Classes",
          diagram_kind: "class",
          source_key: "classes/model.puml"
        }
      ])
    );
    const connector = createAkdbConnector(context);

    const result = await connector.listNormativeDiagrams("tiny-tool-development");

    expect(result.ok).toBe(true);
    expect(result.data).toEqual([
      {
        diagramId: "model",
        title: "Core Classes",
        diagramKind: "class",
        sourceKey: "classes/model.puml"
      }
    ]);
  });

  it("fetchDiagramSource returns raw PlantUML source", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        diagram_id: "model",
        notation: "plantuml",
        raw_source: "@startuml\nclass A\n@enduml\n"
      })
    );
    const connector = createAkdbConnector(context);

    const result = await connector.fetchDiagramSource("model");

    expect(result.ok).toBe(true);
    expect(result.data).toMatchObject({
      diagramId: "model",
      notation: "plantuml",
      source: "@startuml\nclass A\n@enduml\n"
    });
  });

  it("exportAndStage writes PlantUML and provenance under export root", async () => {
    const exportRoot = await mkdtemp(path.join(tmpdir(), "aiagmw-export-"));
    try {
      const connector = createAkdbConnector({ ...context, exportRoot });
      const result = await connector.exportAndStage(
        "@startuml\nclass Staged\n@enduml",
        "Plugins/AIaGMW/classes/staged.puml",
        {
          connector: "akdb",
          source: "workspace-export",
          fetchedAt: new Date().toISOString()
        }
      );

      expect(result.ok).toBe(true);
      const stagedPath = path.join(exportRoot, "Plugins/AIaGMW/classes/staged.puml");
      const staged = await readFile(stagedPath, "utf8");
      expect(staged).toContain("class Staged");
      const provenance = JSON.parse(await readFile(`${stagedPath}.provenance.json`, "utf8")) as { connector: string };
      expect(provenance.connector).toBe("akdb");
    } finally {
      await rm(exportRoot, { recursive: true, force: true });
    }
  });

  it("returns diagnostics instead of throwing on HTTP failures", async () => {
    fetchMock.mockResolvedValueOnce(new Response("service unavailable", { status: 503 }));
    const connector = createAkdbConnector(context);

    const result = await connector.fetchContextPack("offline task");

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/503/);
    expect(result.diagnostics?.[0]?.category).toBe("connector");
  });
});

describe("connector registry", () => {
  afterEach(() => {
    delete process.env.AIAGMW_CONNECTORS_ENABLED;
  });

  it("parses enabled connectors from env", () => {
    process.env.AIAGMW_CONNECTORS_ENABLED = "akdb, git ,akdb";
    expect(parseEnabledConnectors()).toEqual(["akdb", "git"]);
  });

  it("registers akdb connector only when enabled", () => {
    process.env.AIAGMW_CONNECTORS_ENABLED = "akdb";
    const connector = getAkdbConnector({
      akdbUrl: "http://127.0.0.1:8787",
      akdbProjectId: "tiny-tool-development",
      exportRoot: tmpdir()
    });
    expect(connector).not.toBeNull();
  });

  it("probes akdb health when enabled", async () => {
    process.env.AIAGMW_CONNECTORS_ENABLED = "akdb";
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response("ok", { status: 200 }));
    const status = await probeConnectorStatus(
      {
        akdbUrl: "http://127.0.0.1:8787",
        akdbProjectId: "tiny-tool-development",
        exportRoot: tmpdir(),
        fetchImpl: fetchMock
      },
      ["akdb"]
    );

    expect(status).toEqual([{ id: "akdb", enabled: true, reachable: true }]);
  });
});
