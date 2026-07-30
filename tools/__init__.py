"""
tools/__init__.py

Auto-discovers all tool modules in this package AND builds the Ollama
function-calling schemas from each tool's signature + docstring. To add a
new tool:
  1. Create a new .py file in this directory (e.g. my_tool.py)
  2. Define your function(s) with type hints and a docstring
  3. Export a TOOLS dict: TOOLS = {"function_name": function}

That's it — the JSON schema Ollama needs is generated automatically from the
function signature (parameter names, types, defaults) and its Google-style
docstring (summary + Args: descriptions). No schema to hand-write anywhere.
"""
import importlib
import inspect
import pkgutil
import re

AVAILABLE_TOOLS = {}

for module_info in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f".{module_info.name}", package=__name__)
    if hasattr(module, "TOOLS"):
        AVAILABLE_TOOLS.update(module.TOOLS)


# ---------------------------------------------------------------------------
# Schema generation (function signature + docstring -> Ollama tool schema)
# ---------------------------------------------------------------------------
_JSON_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _parse_arg_docs(docstring: str) -> dict:
    """Extracts per-parameter descriptions from a Google-style Args: block."""
    docs = {}
    in_args = False
    current = None
    for line in (docstring or "").splitlines():
        stripped = line.strip()
        if stripped in ("Args:", "Arguments:"):
            in_args = True
            continue
        if not in_args:
            continue
        if stripped in ("Returns:", "Raises:", "Yields:"):
            break
        m = re.match(r"(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)", stripped)
        if m:
            current = m.group(1)
            docs[current] = m.group(2).strip()
        elif current and stripped:
            docs[current] += " " + stripped
    return docs


def _build_schema(name: str, fn) -> dict:
    """Builds one Ollama function-calling schema entry for a tool function."""
    doc = inspect.getdoc(fn) or ""
    summary = doc.split("\n\n")[0].replace("\n", " ").strip() or name
    arg_docs = _parse_arg_docs(doc)

    props = {}
    required = []
    for pname, p in inspect.signature(fn).parameters.items():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        prop = {"type": _JSON_TYPES.get(p.annotation, "string")}
        if pname in arg_docs:
            prop["description"] = arg_docs[pname]
        props[pname] = prop
        if p.default is inspect.Parameter.empty:
            required.append(pname)

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": summary,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        },
    }


TOOL_SCHEMAS = [_build_schema(name, fn) for name, fn in AVAILABLE_TOOLS.items()]
