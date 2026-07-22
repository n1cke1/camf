import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from camf import model, package

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "examples" / "minimal"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def psi_schema():
    return Draft202012Validator(load(ROOT / "spec" / "psi.schema.json"))


@pytest.fixture(scope="module")
def manifest_schema():
    return Draft202012Validator(load(ROOT / "spec" / "package.schema.json"))


def test_schemas_are_themselves_valid(psi_schema, manifest_schema):
    Draft202012Validator.check_schema(psi_schema.schema)
    Draft202012Validator.check_schema(manifest_schema.schema)


def test_minimal_psi_validates(psi_schema):
    psi_schema.validate(load(MINIMAL / "psi.json"))


def test_generated_manifest_validates(manifest_schema):
    rows = model.read_edges_csv(MINIMAL / "edges.csv")
    manifest, _ = package.build_package(rows, load(MINIMAL / "psi.json"), {"checks": []})
    manifest_schema.validate(manifest)


def test_factor_without_source_is_rejected(psi_schema):
    psi = load(MINIMAL / "psi.json")
    del psi["emission_factors"][0]["source"]
    assert not psi_schema.is_valid(psi)


def test_unknown_allocation_rule_is_rejected(psi_schema):
    psi = load(MINIMAL / "psi.json")
    psi["allocation"]["rule"] = "whatever-fits"
    assert not psi_schema.is_valid(psi)


def test_manifest_rejects_foreign_chunk_size(manifest_schema):
    rows = model.read_edges_csv(MINIMAL / "edges.csv")
    manifest, _ = package.build_package(rows, load(MINIMAL / "psi.json"), {"checks": []})
    manifest["merkle"]["chunk_rows"] = 4096
    assert not manifest_schema.is_valid(manifest)


def test_manifest_rejects_truncated_root(manifest_schema):
    rows = model.read_edges_csv(MINIMAL / "edges.csv")
    manifest, _ = package.build_package(rows, load(MINIMAL / "psi.json"), {"checks": []})
    manifest["package_root"] = manifest["package_root"][:32]
    assert not manifest_schema.is_valid(manifest)
