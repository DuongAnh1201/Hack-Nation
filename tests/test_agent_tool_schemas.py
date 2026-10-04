"""Agent tool wrappers must accept the fields agents send.

In strict mode, Omnigent turns a bare ``dict`` parameter into an object schema with no
allowed properties, so every field is rejected (seen in run smoke01: write_record and
log_to_common_knowledge failed on every call). Wrappers with free-form dict parameters
must use ``@tool(strict=False)``.

Needs ``omnigent_client``, which lives in Omnigent's own environment, so this test is
skipped in an environment without it (such as the project ``.venv``).
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("omnigent_client")

AGENTS = Path(__file__).resolve().parents[1] / "backend" / "app" / "agents"
WRAPPERS = sorted(AGENTS.rglob("tools/python/*.py"))


def _tool_metadata(path):
    spec = importlib.util.spec_from_file_location(f"wrapper_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for value in vars(module).values():
        metadata = getattr(value, "_omnigent_tool_metadata", None)
        if metadata is not None:
            return metadata if isinstance(metadata, dict) else vars(metadata)
    raise AssertionError(f"no @tool function in {path}")


@pytest.mark.parametrize("path", WRAPPERS, ids=lambda p: str(p.relative_to(AGENTS)))
def test_no_object_parameter_rejects_every_field(path):
    schema = _tool_metadata(path)["json_schema"]
    for name, prop in schema.get("properties", {}).items():
        closed = (
            prop.get("type") == "object"
            and prop.get("additionalProperties") is False
            and not prop.get("properties")
        )
        assert not closed, f"{path.name}: parameter {name!r} accepts no fields; use @tool(strict=False)"
