import json
from pathlib import Path

import pytest

from camf import canon, model, package

MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal"

# Frozen in examples/minimal/EXPECTED.md. A change here means the
# canonicalization rules changed and the spec version must move with them.
EDGES_ROOT = "7b9391f006843ceacdbb963bddf70eb6ad6b0ec95cfd6b749048f7023449087f"
PSI_ROOT = "57fcde11fb9f440fa4f1721bc1b4edb368e4e9d8940728c5dcb8a97bc5b2eacf"


@pytest.fixture(scope="module")
def rows():
    return model.read_edges_csv(MINIMAL / "edges.csv")


def test_edges_root_is_frozen(rows):
    _, root = package.table_object(rows)
    assert canon.hexroot(root) == EDGES_ROOT


def test_psi_root_is_frozen():
    psi = json.loads((MINIMAL / "psi.json").read_text(encoding="utf-8"))
    assert canon.hexroot(canon.blob_root(canon.jcs(psi))) == PSI_ROOT


def test_root_is_independent_of_input_order(rows):
    _, a = package.table_object(rows)
    _, b = package.table_object(list(reversed(rows)))
    assert a == b


def test_duplicate_key_rejected(rows):
    with pytest.raises(ValueError, match="duplicate composite key"):
        package.table_object(rows + [rows[0]])


def test_manifest_reports_every_object(rows):
    manifest, roots = package.build_package(rows, {"a": 1}, {"checks": []})
    assert [o["name"] for o in manifest["objects"]] == ["diagnostics", "edges", "psi"]
    assert set(roots) == {"edges", "psi", "diagnostics"}
    assert manifest["merkle"] == {"chunk_rows": canon.CHUNK_ROWS, "odd_node": "promote"}


def test_package_root_covers_diagnostics(rows):
    a, _ = package.build_package(rows, {"a": 1}, {"checks": []})
    b, _ = package.build_package(rows, {"a": 1}, {"checks": [{"id": 1}]})
    assert a["package_root"] != b["package_root"]
