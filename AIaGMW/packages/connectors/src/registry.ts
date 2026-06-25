import { createAkdbConnector, type AkdbConnector } from "./akdb/akdbConnector";
import type { ConnectorContext, ConnectorDescriptor, ConnectorStatusEntry } from "./types";

const CONNECTOR_DESCRIPTORS: ConnectorDescriptor[] = [
  {
    id: "akdb",
    label: "ArchitecturalKnowledgeDB",
    capabilities: ["context-pack", "list-diagrams", "fetch-diagram", "export-stage"]
  }
];

export function parseEnabledConnectors(raw = process.env.AIAGMW_CONNECTORS_ENABLED): string[] {
  if (!raw?.trim()) {
    return [];
  }
  return [...new Set(raw.split(",").map((entry) => entry.trim().toLowerCase()).filter(Boolean))];
}

export function listConnectorDescriptors(): ConnectorDescriptor[] {
  return CONNECTOR_DESCRIPTORS;
}

export function isConnectorEnabled(connectorId: string, enabled = parseEnabledConnectors()): boolean {
  return enabled.includes(connectorId.toLowerCase());
}

export function getAkdbConnector(context: ConnectorContext, enabled = parseEnabledConnectors()): AkdbConnector | null {
  if (!isConnectorEnabled("akdb", enabled)) {
    return null;
  }
  return createAkdbConnector(context);
}

export async function probeConnectorStatus(context: ConnectorContext, enabled = parseEnabledConnectors()): Promise<ConnectorStatusEntry[]> {
  const fetchImpl = context.fetchImpl ?? fetch;
  const entries: ConnectorStatusEntry[] = [];

  for (const descriptor of CONNECTOR_DESCRIPTORS) {
    const id = descriptor.id;
    const entry: ConnectorStatusEntry = { id, enabled: isConnectorEnabled(id, enabled) };
    if (!entry.enabled) {
      entries.push(entry);
      continue;
    }

    if (id === "akdb") {
      try {
        const response = await fetchImpl(`${context.akdbUrl.replace(/\/+$/, "")}/health`, { method: "GET" });
        entry.reachable = response.ok;
        if (!response.ok) {
          entry.error = `AKDB health check failed (${response.status}).`;
        }
      } catch (error) {
        entry.reachable = false;
        entry.error = error instanceof Error ? error.message : "AKDB health check failed.";
      }
    }

    entries.push(entry);
  }

  return entries;
}
