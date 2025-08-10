"""Generate TypeScript API types & minimal client from OpenAPI spec.

Steps:
1. Ensure openapi.json exists (invoke generate_openapi if missing).
2. Produce a types file (`frontend/web/src/api/types.ts`) with interfaces.
3. Produce a lightweight fetch wrapper (`frontend/web/src/api/client.ts`).

This avoids adding a heavy dependency; for large schemas consider openapi-typescript.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OPENAPI_PATH = Path("backend/architecture/openapi.json")
TYPES_OUT = Path("frontend/web/src/api/types.ts")
CLIENT_OUT = Path("frontend/web/src/api/client.ts")

HEADER = """// AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
// Run: python backend/scripts/generate_typescript_client.py
"""


def load_spec() -> dict[str, Any]:
    if not OPENAPI_PATH.exists():
        raise SystemExit("openapi.json not found. Run generate_openapi script first.")
    return json.loads(OPENAPI_PATH.read_text())


def ts_type(schema: dict[str, Any]) -> str:
    if not schema:
        return "any"
    t = schema.get("type")
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        return ref
    if t == "string":
        if schema.get("enum"):
            return " | ".join([json.dumps(v) for v in schema["enum"]])
        return "string"
    if t == "integer" or t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        return f"{ts_type(schema.get('items', {}))}[]"
    if t == "object" or schema.get("properties"):
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        parts = []
        for name, sub in props.items():
            optional = "?" if name not in required else ""
            parts.append(f"  {name}{optional}: {ts_type(sub)};")
        return "{\n" + "\n".join(parts) + "\n}"
    return "any"


def emit_types(spec: dict[str, Any]) -> str:
    comps = spec.get("components", {}).get("schemas", {})
    lines = [HEADER]
    for name, schema in comps.items():
        # Ensure SearchResultItem[] becomes explicit in SearchResponse if generic any used
        lines.append(f"export interface {name} {ts_type(schema)}")
    return "\n".join(lines) + "\n"


CLIENT_TEMPLATE = (
    """{header}import type {{ SearchRequest, SearchResponse, SearchResultItem }} from './types';

export interface ApiClientOptions {{ baseUrl?: string; fetchImpl?: typeof fetch; }}

export class ApiClient {{
  private baseUrl: string;
  private fetchImpl: typeof fetch;
  constructor(opts: ApiClientOptions = {{}}) {{
    this.baseUrl = opts.baseUrl || '/api';
    this.fetchImpl = opts.fetchImpl || fetch;
  }}

    async search(body: SearchRequest, init?: RequestInit): Promise<SearchResponse> {{
    const res = await this.fetchImpl(`${{this.baseUrl}}/search`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body),
      ...(init || {{}})
    }});
    if (!res.ok) throw new Error(`Search failed: ${{res.status}}`);
    return res.json();
  }}
}}
"""
)


def emit_client() -> str:
    return CLIENT_TEMPLATE.format(header=HEADER)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def main() -> int:
    spec = load_spec()
    types_code = emit_types(spec)
    client_code = emit_client()
    changed = write_if_changed(TYPES_OUT, types_code)
    changed_client = write_if_changed(CLIENT_OUT, client_code)
    print("Updated:" if (changed or changed_client) else "No changes", TYPES_OUT, CLIENT_OUT)
    return 0

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
