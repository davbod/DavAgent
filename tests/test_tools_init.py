import tools
from tools import _build_schema, _parse_arg_docs


def sample_tool(path: str, count: int = 5, flag: bool = False):
    """Does a sample thing.

    Args:
        path: The path to use.
        count: How many times.
        flag: Whether to flag it.

    Returns:
        A string.
    """
    return "ok"


def no_doc_tool(x):
    return x


def test_parse_arg_docs_extracts_descriptions():
    docs = _parse_arg_docs(sample_tool.__doc__)
    assert docs["path"] == "The path to use."
    assert docs["count"] == "How many times."
    assert docs["flag"] == "Whether to flag it."


def test_parse_arg_docs_stops_at_returns_section():
    docs = _parse_arg_docs(sample_tool.__doc__)
    assert "Returns" not in docs
    assert len(docs) == 3


def test_build_schema_maps_types_and_required():
    schema = _build_schema("sample_tool", sample_tool)
    fn_schema = schema["function"]
    assert fn_schema["name"] == "sample_tool"
    assert fn_schema["description"] == "Does a sample thing."

    props = fn_schema["parameters"]["properties"]
    assert props["path"]["type"] == "string"
    assert props["count"]["type"] == "integer"
    assert props["flag"]["type"] == "boolean"
    assert props["path"]["description"] == "The path to use."

    # Only params without defaults are required.
    assert fn_schema["parameters"]["required"] == ["path"]


def test_build_schema_handles_missing_docstring_gracefully():
    schema = _build_schema("no_doc_tool", no_doc_tool)
    fn_schema = schema["function"]
    assert fn_schema["description"] == "no_doc_tool"
    assert fn_schema["parameters"]["properties"]["x"]["type"] == "string"
    assert fn_schema["parameters"]["required"] == ["x"]


def test_all_available_tools_have_valid_schemas():
    # Every registered tool must produce a schema pytest can round-trip: a
    # name, a non-empty description, and required params that are a subset
    # of the declared properties.
    names_seen = set()
    for schema in tools.TOOL_SCHEMAS:
        fn = schema["function"]
        assert fn["name"]
        assert fn["description"]
        props = set(fn["parameters"]["properties"])
        required = set(fn["parameters"]["required"])
        assert required <= props
        names_seen.add(fn["name"])

    assert names_seen == set(tools.AVAILABLE_TOOLS)


def test_deprecated_and_placeholder_tools_are_not_registered():
    # folder_contents.list_folder_contents and esp32_relay.trigger_esp32_relay
    # intentionally export empty TOOLS dicts; make sure that stays true so
    # they don't silently reappear in the model's tool list.
    assert "list_folder_contents" not in tools.AVAILABLE_TOOLS
    assert "trigger_esp32_relay" not in tools.AVAILABLE_TOOLS
