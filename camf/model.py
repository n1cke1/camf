"""Edge table -> technology matrix -> upstream cone -> sparse solve.

Normative form (spec/CAMF-1.0.md §4):

    (I - A) x_p = y_p        x_p  full upstream activity per unit of p
    PCF_k(p)    = f_k^T x_p  f_k  extension vector k, per unit of node output

The stored form is the *unnormalised* edge table in ERP physical units, since
that is what a verifier reconciles against transaction records. A is derived
from it by the normalisation rule, never stored.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

SCHEMA = [
    ("plant", "str"), ("product", "str"), ("component", "str"), ("period", "str"),
    ("unit", "str"), ("coefficient", "f64"), ("data_quality", "str"),
    ("method", "str"), ("params", "str"), ("emission_formula", "str"),
    ("co2e", "f64"), ("S1", "int"), ("S2", "int"), ("S3", "int"),
    ("CBAM_d", "int"), ("CBAM_i", "int"), ("produced_qty", "f64"),
    ("consumed_total", "f64"), ("residual", "f64"), ("legal_entity", "str"),
]
COLUMNS = [c for c, _ in SCHEMA]
TYPES = [t for _, t in SCHEMA]
KEY = ("plant", "product", "component", "period")
KEY_POSITIONS = [COLUMNS.index(c) for c in KEY]


@dataclass
class Model:
    nodes: list          # node ids, sorted -- index order is part of the spec
    index: dict          # node id -> position
    A: sp.csc_matrix     # a[j,i] = input j per unit output of i
    f_dir: np.ndarray    # direct intensity per unit output
    q: np.ndarray        # gross output per node (0.0 for external leaves)


def read_edges_csv(path) -> list:
    """Read an edge table into rows ordered by the schema."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = []
        for rec in csv.DictReader(fh):
            row = []
            for col, kind in SCHEMA:
                raw = rec.get(col, "")
                if raw == "":
                    row.append(None if kind == "str" else 0.0 if kind == "f64" else 0)
                else:
                    row.append(raw if kind == "str" else
                               float(raw) if kind == "f64" else int(raw))
            rows.append(row)
    return rows


def build(rows) -> Model:
    """Build A and f_dir from the edge table (normalisation rule, spec §4.2)."""
    col = {c: i for i, c in enumerate(COLUMNS)}
    nodes = sorted({r[col["product"]] for r in rows} | {r[col["component"]] for r in rows})
    index = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)

    q = np.zeros(n)
    f_dir = np.zeros(n)
    for r in rows:
        if r[col["product"]] == r[col["component"]]:
            i = index[r[col["product"]]]
            if q[i]:
                raise ValueError(f"duplicate diagonal row for node {nodes[i]!r}")
            q[i] = -r[col["coefficient"]]
            if q[i] <= 0:
                raise ValueError(f"non-positive gross output for node {nodes[i]!r}")
            f_dir[i] = r[col["co2e"]] / q[i]

    data, rowi, coli = [], [], []
    for r in rows:
        i_id, j_id = r[col["product"]], r[col["component"]]
        if i_id == j_id:
            continue
        i = index[i_id]
        if q[i] == 0.0:
            raise ValueError(f"node {i_id!r} consumes inputs but has no output row")
        data.append(r[col["coefficient"]] / q[i])
        rowi.append(index[j_id])
        coli.append(i)

    A = sp.csc_matrix((data, (rowi, coli)), shape=(n, n))
    return Model(nodes, index, A, f_dir, q)


def cone(model: Model, product: str) -> list:
    """Upstream cone of a product: BFS against edge direction, sorted."""
    start = model.index[product]
    A, seen, queue = model.A, {start}, [start]
    while queue:
        i = queue.pop()
        for j in A.indices[A.indptr[i]:A.indptr[i + 1]]:
            if j not in seen:
                seen.add(int(j))
                queue.append(int(j))
    return sorted(seen)


def solve(A: sp.csc_matrix, y: np.ndarray) -> np.ndarray:
    """Solve (I - A) x = y by sparse LU."""
    n = A.shape[0]
    return spla.splu((sp.identity(n, format="csc") - A).tocsc()).solve(y)


def solve_cone(model: Model, product: str):
    """Restricted solve. Returns (cone node positions, x on the cone)."""
    idx = cone(model, product)
    A_c = model.A[idx, :][:, idx]
    y = np.zeros(len(idx))
    y[idx.index(model.index[product])] = 1.0
    return idx, solve(sp.csc_matrix(A_c), y)


def pcf(model: Model, product: str, mask: np.ndarray | None = None) -> float:
    """Product carbon footprint per unit output: f^T x, optionally masked."""
    idx, x = solve_cone(model, product)
    f = model.f_dir[idx] if mask is None else (model.f_dir * mask)[idx]
    return float(f @ x)


def residual(model: Model, product: str) -> float:
    """Relative solver residual ||(I - A) x - y|| / ||y|| on the cone."""
    idx, x = solve_cone(model, product)
    A_c = sp.csc_matrix(model.A[idx, :][:, idx])
    y = np.zeros(len(idx))
    y[idx.index(model.index[product])] = 1.0
    return float(np.linalg.norm((sp.identity(len(idx), format="csc") - A_c) @ x - y)
                 / np.linalg.norm(y))


def pcf_full(model: Model, product: str) -> float:
    """Same quantity solved on the full system -- reconciliation check 3."""
    y = np.zeros(len(model.nodes))
    y[model.index[product]] = 1.0
    return float(model.f_dir @ solve(model.A, y))


def intensities_dual(model: Model) -> np.ndarray:
    """Intensity (dual) form: (I - A^T) f = f_dir, as implemented internally.

    Provided to demonstrate the equivalence asserted in spec §4.3, not used by
    the reference pipeline.
    """
    return solve(sp.csc_matrix(model.A.T), model.f_dir)
