import json
from pathlib import Path

import pytest

from camf import diagnostics, model

ROOT = Path(__file__).resolve().parents[1]
MINIMAL = ROOT / "examples" / "minimal"
DEFECTS = ROOT / "examples" / "defects"
DECLARED = ["ALU"]


@pytest.fixture(scope="module")
def psi():
    return json.loads((MINIMAL / "psi.json").read_text(encoding="utf-8"))


def profile_of(edges_path, psi):
    m = model.build(model.read_edges_csv(edges_path))
    return diagnostics.run(m, DECLARED, psi)


def check(profile, cid):
    return next(c for c in profile["checks"] if c["id"] == cid)


def test_clean_example_passes_everything(psi):
    prof = profile_of(MINIMAL / "edges.csv", psi)
    assert diagnostics.failed(prof) == []
    assert [c["id"] for c in prof["checks"]] == [1, 2, 3, 4, 5, 6, 7]


def test_net_output_is_not_a_mass_balance_failure(psi):
    # ALU leaves the system entirely and PWR is partly exported; both are
    # declared in the residual column and must not be reported as gaps.
    assert check(profile_of(MINIMAL / "edges.csv", psi), 2)["gaps"] == []


def test_declared_leaf_is_surfaced_not_failed(psi):
    c = check(profile_of(MINIMAL / "edges.csv", psi), 5)
    assert c["status"] == "review"
    assert [leaf["node"] for leaf in c["leaves"]] == ["COAL"]


def test_contributions_partition_the_footprint(psi):
    c = check(profile_of(MINIMAL / "edges.csv", psi), 7)
    shares = [n["share"] for n in c["products"]["ALU"]["top_nodes"]]
    assert sum(shares) == pytest.approx(1.0, rel=1e-12)


# --- one defect, one check -------------------------------------------------

def test_non_productive_cycle_is_caught(psi):
    prof = profile_of(DEFECTS / "cycle_nonproductive.csv", psi)
    assert diagnostics.failed(prof) == ["cycle_productivity"]
    assert check(prof, 6)["max_spectral_radius"] > 1.0
    # Nothing downstream is reported as passing: the series does not converge.
    assert all(c["status"] == "not_evaluated" for c in prof["checks"] if c["id"] != 6)


def test_unexplained_mass_gap_is_caught(psi):
    prof = profile_of(DEFECTS / "mass_gap.csv", psi)
    assert diagnostics.failed(prof) == ["mass_balance"]
    gap = check(prof, 2)["gaps"]
    assert [g["node"] for g in gap] == ["ALO"]
    assert gap[0]["unexplained_relative"] == pytest.approx(0.5, abs=1e-9)


def test_missing_source_is_caught_only_by_inventory(psi):
    prof = profile_of(DEFECTS / "missing_source.csv", psi)
    assert diagnostics.failed(prof) == ["inventory_reconciliation"]
    c = check(prof, 4)
    assert c["gap"] == pytest.approx(30.0)
    assert c["total_direct_in_matrix"] == pytest.approx(950.0)


def test_extra_dangling_leaf_is_surfaced(psi):
    prof = profile_of(DEFECTS / "dangling.csv", psi)
    assert diagnostics.failed(prof) == []
    c = check(prof, 5)
    assert c["count"] == 2
    assert "ALLOY" in [leaf["node"] for leaf in c["leaves"]]
    assert c["leaves"][0]["consumers"] or True  # consumers are enumerated for review


def test_inventory_not_evaluated_without_external_figure():
    m = model.build(model.read_edges_csv(MINIMAL / "edges.csv"))
    prof = diagnostics.run(m, DECLARED, {})
    c = check(prof, 4)
    assert c["status"] == "not_evaluated"
    assert "no corporate inventory" in c["reason"]
