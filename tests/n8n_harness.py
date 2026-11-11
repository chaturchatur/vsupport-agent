"""Helpers for testing the JavaScript that lives inside n8n Code nodes.

The parsing and mapping logic of this project is JavaScript embedded in the
workflow exports under ``n8n/workflows/``. Rather than re-implementing it in
Python (which would test a copy, not the code that runs), these helpers pull the
``jsCode`` out of the workflow JSON and execute it with Node.js, stubbing the two
n8n globals the nodes use (``$input`` and ``$('Node Name')``).

Requires ``node`` on PATH. Tests that need it are skipped, with a reason, when it
is missing.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / "n8n" / "workflows"
RUNNER = Path(__file__).resolve().parent / "run_code_node.js"


def load_workflow(name: str) -> dict:
    """Load ``n8n/workflows/<name>.json``."""
    return json.loads((WORKFLOWS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def get_node(workflow: dict, node_name: str) -> dict:
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            return node
    raise KeyError(node_name)


def run_code_node(
    workflow_name: str,
    node_name: str,
    input_items: list,
    nodes: dict | None = None,
    workflow_path: Path | None = None,
) -> list:
    """Execute one Code node and return the ``json`` of every item it emitted.

    ``workflow_path`` runs the node from another copy of the workflow, e.g. one
    with deploy-time placeholders resolved.
    """
    node_bin = shutil.which("node")
    if node_bin is None:
        pytest.skip("Node.js is not installed; it is needed to execute n8n Code node JavaScript")
    request = {
        "workflow": str(workflow_path or WORKFLOWS_DIR / f"{workflow_name}.json"),
        "node": node_name,
        "input": input_items,
        "nodes": nodes or {},
    }
    proc = subprocess.run(
        [node_bin, str(RUNNER)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert proc.returncode == 0, f"{node_name} failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


def resolved_copy(workflow_name: str, values: dict, directory: Path) -> Path:
    """Write a copy of a workflow with ``__NAME__`` placeholders filled in, as deploy-n8n.sh does."""
    text = (WORKFLOWS_DIR / f"{workflow_name}.json").read_text(encoding="utf-8")
    for name, value in values.items():
        text = text.replace(f"__{name}__", value)
    path = Path(directory) / f"{workflow_name}.json"
    path.write_text(text, encoding="utf-8")
    return path
