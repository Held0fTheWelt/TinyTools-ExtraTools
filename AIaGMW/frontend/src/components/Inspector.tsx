import { useEffect, useState } from "react";
import type { RelationKind, UmlElement, UmlMethod, UmlProperty, UmlRelation } from "@aiagmw/shared";

const relationKinds: RelationKind[] = [
  "association",
  "dependency",
  "inheritance",
  "implementation",
  "composition",
  "aggregation",
  "realization",
  "containment",
  "uses",
  "creates",
  "owns",
  "publishes",
  "subscribes",
  "calls"
];

interface InspectorProps {
  element: (UmlElement & { modelId: string }) | null;
  relation: (UmlRelation & { modelId: string }) | null;
  onSaveElement: (modelId: string, elementId: string, updates: Partial<UmlElement>) => void;
  onSaveRelation: (modelId: string, relationId: string, updates: Partial<UmlRelation>) => void;
  onRemoveElementFromDiagram: (modelId: string, elementId: string) => void;
  onDeleteElementFromModel: (modelId: string, elementId: string) => void;
  onRemoveRelationFromDiagram: (modelId: string, relationId: string) => void;
  onDeleteRelationFromModel: (modelId: string, relationId: string) => void;
}

export function Inspector({
  element,
  relation,
  onSaveElement,
  onSaveRelation,
  onRemoveElementFromDiagram,
  onDeleteElementFromModel,
  onRemoveRelationFromDiagram,
  onDeleteRelationFromModel
}: InspectorProps) {
  const [elementName, setElementName] = useState("");
  const [elementVisibility, setElementVisibility] = useState("");
  const [elementAbstract, setElementAbstract] = useState(false);
  const [elementStereotypes, setElementStereotypes] = useState("");
  const [responsibilities, setResponsibilities] = useState("");
  const [properties, setProperties] = useState("");
  const [methods, setMethods] = useState("");
  const [elementTags, setElementTags] = useState("");
  const [relationName, setRelationName] = useState("");
  const [relationKind, setRelationKind] = useState<RelationKind>("association");
  const [relationTags, setRelationTags] = useState("");
  const [fromMultiplicity, setFromMultiplicity] = useState("");
  const [toMultiplicity, setToMultiplicity] = useState("");
  const [navigability, setNavigability] = useState("");
  const [relationFrom, setRelationFrom] = useState("");
  const [relationTo, setRelationTo] = useState("");
  const [relationStereotypes, setRelationStereotypes] = useState("");
  const [fromRole, setFromRole] = useState("");
  const [toRole, setToRole] = useState("");
  const [enumLiterals, setEnumLiterals] = useState("");

  useEffect(() => {
    setElementName(element?.name ?? "");
    setElementVisibility(element?.visibility ?? "");
    setElementAbstract(element?.abstract ?? false);
    setElementStereotypes((element?.stereotypes ?? []).join(", "));
    setResponsibilities((element?.responsibilities ?? []).join("\n"));
    setProperties(formatProperties(element?.properties ?? []));
    setMethods(formatMethods(element?.methods ?? []));
    setElementTags((element?.tags ?? []).join(", "));
    setEnumLiterals((element?.constraints ?? []).join("\n"));
  }, [element]);

  useEffect(() => {
    setRelationName(relation?.name ?? "");
    setRelationKind(relation?.kind ?? "association");
    setRelationTags((relation?.tags ?? []).join(", "));
    setFromMultiplicity(relation?.fromMultiplicity ?? "");
    setToMultiplicity(relation?.toMultiplicity ?? "");
    setNavigability(relation?.navigability ?? "");
    setRelationFrom(relation?.from ?? "");
    setRelationTo(relation?.to ?? "");
    setRelationStereotypes((relation?.stereotypes ?? []).join(", "));
    setFromRole(String(relation?.metadata?.fromRole ?? ""));
    setToRole(String(relation?.metadata?.toRole ?? ""));
  }, [relation]);

  if (relation) {
    return (
      <form
        className="inspector-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSaveRelation(relation.modelId, relation.id, {
            name: relationName.trim() || relation.kind,
            kind: relationKind,
            from: relationFrom.trim() || relation.from,
            to: relationTo.trim() || relation.to,
            fromMultiplicity: fromMultiplicity.trim() || undefined,
            toMultiplicity: toMultiplicity.trim() || undefined,
            navigability: navigability.trim() || undefined,
            stereotypes: splitCsv(relationStereotypes),
            tags: relationTags
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
            metadata: {
              ...(relation.metadata ?? {}),
              fromRole: fromRole.trim() || undefined,
              toRole: toRole.trim() || undefined
            }
          });
        }}
      >
        <label>
          <span>Name</span>
          <input value={relationName} onChange={(event) => setRelationName(event.target.value)} />
        </label>
        <label>
          <span>Kind</span>
          <select value={relationKind} onChange={(event) => setRelationKind(event.target.value as RelationKind)}>
            {relationKinds.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>From</span>
          <input value={relationFrom} onChange={(event) => setRelationFrom(event.target.value)} />
        </label>
        <label>
          <span>To</span>
          <input value={relationTo} onChange={(event) => setRelationTo(event.target.value)} />
        </label>
        <label>
          <span>From multiplicity</span>
          <input value={fromMultiplicity} onChange={(event) => setFromMultiplicity(event.target.value)} placeholder="0..1" />
        </label>
        <label>
          <span>To multiplicity</span>
          <input value={toMultiplicity} onChange={(event) => setToMultiplicity(event.target.value)} placeholder="1..*" />
        </label>
        <label>
          <span>Navigability</span>
          <input value={navigability} onChange={(event) => setNavigability(event.target.value)} placeholder="bidirectional" />
        </label>
        <label>
          <span>From role</span>
          <input value={fromRole} onChange={(event) => setFromRole(event.target.value)} placeholder="client" />
        </label>
        <label>
          <span>To role</span>
          <input value={toRole} onChange={(event) => setToRole(event.target.value)} placeholder="server" />
        </label>
        <label>
          <span>Stereotypes</span>
          <input value={relationStereotypes} onChange={(event) => setRelationStereotypes(event.target.value)} />
        </label>
        <label>
          <span>Tags</span>
          <input value={relationTags} onChange={(event) => setRelationTags(event.target.value)} />
        </label>
        <button type="submit">Save relation</button>
        <div className="inspector-danger-zone">
          <button
            type="button"
            className="secondary-action"
            onClick={() => onRemoveRelationFromDiagram(relation.modelId, relation.id)}
          >
            Remove from diagram
          </button>
          <button type="button" className="danger-action" onClick={() => onDeleteRelationFromModel(relation.modelId, relation.id)}>
            Delete from model
          </button>
        </div>
      </form>
    );
  }

  if (!element) {
    return <div className="empty-inspector">Select a diagram element or relation.</div>;
  }

  return (
    <form
      className="inspector-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSaveElement(element.modelId, element.id, {
          name: elementName.trim() || element.name,
          visibility: elementVisibility || undefined,
          abstract: elementAbstract,
          stereotypes: splitCsv(elementStereotypes),
          responsibilities: responsibilities
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
          properties: parseProperties(properties),
          methods: parseMethods(methods),
          tags: elementTags
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          constraints:
            element.kind === "enum"
              ? enumLiterals
                  .split("\n")
                  .map((item) => item.trim())
                  .filter(Boolean)
              : element.constraints
        });
      }}
    >
      <label>
        <span>Name</span>
        <input value={elementName} onChange={(event) => setElementName(event.target.value)} />
      </label>
      <label>
        <span>Kind</span>
        <input value={element.kind} disabled />
      </label>
      <label>
        <span>Visibility</span>
        <select value={elementVisibility} onChange={(event) => setElementVisibility(event.target.value)}>
          <option value="">unspecified</option>
          <option value="public">public</option>
          <option value="private">private</option>
          <option value="protected">protected</option>
          <option value="package">package</option>
        </select>
      </label>
      <label className="checkbox-row">
        <input type="checkbox" checked={elementAbstract} onChange={(event) => setElementAbstract(event.target.checked)} />
        <span>Abstract</span>
      </label>
      <label>
        <span>Stereotypes</span>
        <input value={elementStereotypes} onChange={(event) => setElementStereotypes(event.target.value)} />
      </label>
      <label>
        <span>Responsibilities</span>
        <textarea rows={5} value={responsibilities} onChange={(event) => setResponsibilities(event.target.value)} />
      </label>
      <label>
        <span>Properties</span>
        <textarea rows={5} value={properties} onChange={(event) => setProperties(event.target.value)} placeholder="+ name: Type [1]" />
      </label>
      <label>
        <span>Methods</span>
        <textarea rows={5} value={methods} onChange={(event) => setMethods(event.target.value)} placeholder="+ DoThing(input: Type): Result" />
      </label>
      <label>
        <span>Tags</span>
        <input value={elementTags} onChange={(event) => setElementTags(event.target.value)} />
      </label>
      {element.kind === "enum" ? (
        <label>
          <span>Enum literals</span>
          <textarea rows={4} value={enumLiterals} onChange={(event) => setEnumLiterals(event.target.value)} placeholder="ValueA&#10;ValueB" />
        </label>
      ) : null}
      <button type="submit">Save element</button>
      <div className="inspector-danger-zone">
        <button type="button" className="secondary-action" onClick={() => onRemoveElementFromDiagram(element.modelId, element.id)}>
          Remove from diagram
        </button>
        <button type="button" className="danger-action" onClick={() => onDeleteElementFromModel(element.modelId, element.id)}>
          Delete from model
        </button>
      </div>
    </form>
  );
}

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatProperties(properties: UmlProperty[]): string {
  return properties.map((property) => `${visibilitySymbol(property.visibility)}${property.name}: ${property.type ?? ""}${property.multiplicity ? ` [${property.multiplicity}]` : ""}`.trim()).join("\n");
}

function parseProperties(value: string): UmlProperty[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = /^(?:(public|private|protected|package|\+|-|#|~)\s*)?([^:[\]]+?)(?::\s*([^\[]+?))?(?:\s*\[([^\]]+)\])?$/i.exec(line);
      if (!match) {
        return { name: line };
      }

      return {
        name: match[2]?.trim() ?? line,
        type: match[3]?.trim() || undefined,
        visibility: normalizeVisibility(match[1]),
        multiplicity: match[4]?.trim() || undefined
      };
    });
}

function formatMethods(methods: UmlMethod[]): string {
  return methods
    .map((method) => {
      const parameters = (method.parameters ?? [])
        .map((parameter) => `${parameter.name}${parameter.type ? `: ${parameter.type}` : ""}`)
        .join(", ");
      return `${visibilitySymbol(method.visibility)}${method.name}(${parameters})${method.returnType ? `: ${method.returnType}` : ""}`.trim();
    })
    .join("\n");
}

function parseMethods(value: string): UmlMethod[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = /^(?:(public|private|protected|package|\+|-|#|~)\s*)?([^(]+?)\s*\(([^)]*)\)\s*(?::\s*(.+))?$/i.exec(line);
      if (!match) {
        return { name: line };
      }

      return {
        name: match[2]?.trim() ?? line,
        visibility: normalizeVisibility(match[1]),
        parameters: parseParameters(match[3] ?? ""),
        returnType: match[4]?.trim() || undefined
      };
    });
}

function parseParameters(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [name, type] = item.split(":").map((part) => part.trim());
      return {
        name: name || "parameter",
        type: type || undefined
      };
    });
}

function normalizeVisibility(value: string | undefined): string | undefined {
  switch (value) {
    case "+":
      return "public";
    case "-":
      return "private";
    case "#":
      return "protected";
    case "~":
      return "package";
    default:
      return value?.toLowerCase();
  }
}

function visibilitySymbol(value: string | undefined): string {
  switch (value) {
    case "public":
      return "+ ";
    case "private":
      return "- ";
    case "protected":
      return "# ";
    case "package":
      return "~ ";
    default:
      return "";
  }
}
