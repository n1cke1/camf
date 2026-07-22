from pathlib import Path

import numpy as np
import pytest

from camf import model

MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal" / "edges.csv"


@pytest.fixture(scope="module")
def m():
    return model.build(model.read_edges_csv(MINIMAL))


def test_nodes_and_external_leaf(m):
    assert m.nodes == ["ALO", "ALU", "COAL", "PWR", "STM"]
    coal = m.index["COAL"]
    assert m.q[coal] == 0.0          # consumed, never produced
    assert m.f_dir[coal] == 0.0      # zero embedded carbon by construction
    assert m.A[:, coal].nnz == 0


def test_normalisation_rule(m):
    # a[j,i] = c_ij / q_i : 700 MWh of PWR per 50 t of ALU
    assert m.A[m.index["PWR"], m.index["ALU"]] == pytest.approx(14.0)
    assert m.f_dir[m.index["PWR"]] == pytest.approx(0.9)


def test_solver_residual_below_tolerance(m):
    for p in ("ALU", "ALO", "PWR", "STM"):
        assert model.residual(m, p) < 1e-6


def test_cone_is_closed_under_predecessors(m):
    assert [m.nodes[i] for i in model.cone(m, "ALU")] == \
        ["ALO", "ALU", "COAL", "PWR", "STM"]
    # PWR does not consume alumina or aluminium, so they stay out of its cone.
    assert [m.nodes[i] for i in model.cone(m, "PWR")] == ["COAL", "PWR", "STM"]


def test_cone_matches_full_system(m):
    for p in ("ALU", "ALO", "PWR", "STM"):
        assert model.pcf(m, p) == pytest.approx(model.pcf_full(m, p), abs=1e-9)


def test_dual_form_is_equivalent(m):
    # spec §4.3: (I - A^T) f = f_dir gives the same intensities as f_dir^T x_p
    dual = model.intensities_dual(m)
    for p in m.nodes:
        assert dual[m.index[p]] == pytest.approx(model.pcf(m, p), rel=1e-12)


def test_cycle_is_productive(m):
    loop = [m.index["PWR"], m.index["STM"]]
    sub = m.A[loop, :][:, loop].toarray()
    assert max(abs(np.linalg.eigvals(sub))) < 1.0


def test_known_values(m):
    # Hand-solved: e_PWR = 0.905 / 0.997, e_STM = 0.25 + 0.15 e_PWR
    assert model.pcf(m, "PWR") == pytest.approx(0.905 / 0.997, rel=1e-12)
    assert model.pcf(m, "STM") == pytest.approx(0.25 + 0.15 * 0.905 / 0.997, rel=1e-12)


def test_duplicate_diagonal_rejected():
    rows = model.read_edges_csv(MINIMAL)
    with pytest.raises(ValueError, match="duplicate diagonal"):
        model.build(rows + [rows[0]])


def test_consumer_without_output_rejected():
    rows = model.read_edges_csv(MINIMAL)
    orphan = list(rows[1])
    orphan[model.COLUMNS.index("product")] = "GHOST"
    with pytest.raises(ValueError, match="no output row"):
        model.build(rows + [orphan])
