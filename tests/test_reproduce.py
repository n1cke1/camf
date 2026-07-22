import json

import pytest

import reproduce

# Frozen in examples/minimal/EXPECTED.md. Covers the edge table, psi and the
# diagnostic profile at once: any of the three moving changes this value.
PACKAGE_ROOT = "ad711117f6ac75e99d60a1ff8d47777e46d66a0da80870ab074a0b33a75dd1b1"


@pytest.fixture()
def built(tmp_path):
    return reproduce.build(reproduce.DEFAULTS / "edges.csv",
                           reproduce.DEFAULTS / "psi.json", ["ALU"], tmp_path), tmp_path


def test_package_contains_every_object(built):
    _, out = built
    assert sorted(p.name for p in out.iterdir()) == \
        ["diagnostics.json", "edges.csv", "manifest.json", "psi.json"]


def test_package_root_is_frozen(built):
    manifest, _ = built
    assert manifest["package_root"] == PACKAGE_ROOT


def test_verify_accepts_its_own_output(built):
    _, out = built
    assert reproduce.verify(out) == 0


def test_written_package_round_trips_to_the_same_root(built, tmp_path):
    manifest, out = built
    # Rebuild from the written CSV rather than the source example: the
    # transport file must carry the same logical content.
    again = reproduce.build(out / "edges.csv", out / "psi.json", ["ALU"],
                            tmp_path / "again")
    assert again["package_root"] == manifest["package_root"]


def test_two_builds_agree(tmp_path):
    a = reproduce.build(reproduce.DEFAULTS / "edges.csv", reproduce.DEFAULTS / "psi.json",
                        ["ALU"], tmp_path / "a")
    b = reproduce.build(reproduce.DEFAULTS / "edges.csv", reproduce.DEFAULTS / "psi.json",
                        ["ALU"], tmp_path / "b")
    assert a["package_root"] == b["package_root"]
    assert (tmp_path / "a" / "psi.json").read_bytes() == (tmp_path / "b" / "psi.json").read_bytes()


def test_tampering_with_an_edge_breaks_the_root(built, tmp_path):
    manifest, out = built
    text = (out / "edges.csv").read_text(encoding="utf-8").replace("700", "701")
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "edges.csv").write_text(text, encoding="utf-8", newline="")
    tampered = reproduce.build(tmp_path / "t" / "edges.csv", out / "psi.json", ["ALU"],
                               tmp_path / "t" / "pkg")
    assert tampered["package_root"] != manifest["package_root"]


def test_verify_rejects_a_substituted_declaration(built):
    manifest, out = built
    doc = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    doc["products"][0]["pcf"] = 1.0
    (out / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    assert reproduce.verify(out) == 1
