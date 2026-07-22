"""The seven checks of spec/CAMF-1.0.md §5.

Every check is a by-product of the solve, not extra work: the auditor inspects
one fixed object instead of recomputing individual products.

Check 6 runs first and independently of any solve. A non-productive cycle
means the Leontief series diverges, so the checks that need a solution are
reported as `not_evaluated` rather than silently returning nonsense.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

from . import model as _model

PIECE_UNITS = {"pcs", "m", "set", "unit"}
DEFAULT_MASS_BALANCE_TOL = 0.05


def _status(ok: bool) -> str:
    return "pass" if ok else "fail"


def cycle_productivity(m) -> dict:
    """Check 6. Spectral radius of every non-trivial SCC must be below one."""
    n_comp, labels = connected_components(m.A, directed=True, connection="strong")
    cycles, worst = [], 0.0
    for c in range(n_comp):
        idx = np.flatnonzero(labels == c)
        if len(idx) < 2:
            continue
        sub = m.A[idx, :][:, idx].toarray()
        rho = float(max(abs(np.linalg.eigvals(sub))))
        worst = max(worst, rho)
        cycles.append({"nodes": [m.nodes[i] for i in idx], "length": len(idx),
                       "spectral_radius": rho})
    return {"id": 6, "name": "cycle_productivity", "status": _status(worst < 1.0),
            "max_spectral_radius": worst, "cycles": cycles}


def solver_residual(m, declared, tol: float) -> dict:
    per = {p: _model.residual(m, p) for p in declared}
    return {"id": 1, "name": "solver_residual",
            "status": _status(all(v < tol for v in per.values())),
            "tolerance": tol, "per_product": per}


def mass_balance(m, tol: float = DEFAULT_MASS_BALANCE_TOL) -> dict:
    """Check 2. Produced against consumed, per node, within stock movements.

    Net output is legitimate: a final product leaves the system entirely, and
    electricity or steam may be sold. What the declarant records in the
    `residual` column is that explanation. The check tests the part it does
    not explain — produced minus consumed minus declared net output.
    """
    consumed = np.asarray(m.A @ m.q).ravel()
    gaps, excluded = [], []
    for i, node in enumerate(m.nodes):
        if m.q[i] == 0.0:
            continue
        if m.unit[i] in PIECE_UNITS:
            excluded.append(node)
            continue
        rel = (m.q[i] - consumed[i] - m.net_declared[i]) / m.q[i]
        if abs(rel) > tol:
            gaps.append({"node": node, "unit": m.unit[i], "produced": m.q[i],
                         "consumed": float(consumed[i]),
                         "declared_net_output": float(m.net_declared[i]),
                         "unexplained_relative": float(rel)})
    return {"id": 2, "name": "mass_balance", "status": _status(not gaps),
            "tolerance": tol, "gaps": gaps, "excluded_piece_units": excluded}


def cone_vs_full(m, declared, tol: float) -> dict:
    """Check 3. The restricted solution is an identity, not an approximation."""
    per = {p: abs(_model.pcf(m, p) - _model.pcf_full(m, p)) for p in declared}
    return {"id": 3, "name": "cone_vs_full",
            "status": _status(all(v < tol for v in per.values())),
            "tolerance": tol, "per_product": per}


def inventory_reconciliation(m, declared, inventory_total=None, tol: float = 1e-6) -> dict:
    """Check 4. Matrix against the corporate direct-emissions inventory.

    This is the one check that reaches outside the package: `inventory_total`
    is the externally reported figure. A gap means the graph is missing a
    source, which no internal consistency check can reveal.

    Within the matrix, net output times intensity summed over *all* nodes
    equals total direct emissions identically, so the informative split is
    between what reaches a declared product and what does not: emissions on
    nodes lying in no cone enter no PCF at all.
    """
    e = _model.intensities_dual(m)
    net = m.q - np.asarray(m.A @ m.q).ravel()
    total_direct = float(m.f_dir @ m.q)
    attributed = float(sum(net[m.index[p]] * e[m.index[p]] for p in declared))

    in_cone = set()
    for p in declared:
        in_cone.update(_model.cone(m, p))
    outside = [{"node": m.nodes[i], "direct_co2e": float(m.f_dir[i] * m.q[i])}
               for i in range(len(m.nodes)) if m.f_dir[i] != 0.0 and i not in in_cone]

    out = {"id": 4, "name": "inventory_reconciliation",
           "total_direct_in_matrix": total_direct,
           "attributed_to_declared": attributed,
           "carried_by_other_net_output": total_direct - attributed,
           "nodes_outside_every_cone": outside}
    if inventory_total is None:
        out["status"] = "not_evaluated"
        out["reason"] = "no corporate inventory figure supplied in psi"
        return out
    gap = inventory_total - total_direct
    out["corporate_inventory_co2e"] = float(inventory_total)
    out["gap"] = gap
    out["status"] = _status(abs(gap) <= tol * max(1.0, abs(inventory_total)))
    return out


def dangling_leaves(m) -> dict:
    """Check 5. Consumed but never produced: zero embedded carbon by construction."""
    consumed = np.asarray(m.A @ m.q).ravel()
    leaves = [{"node": m.nodes[i], "consumed_qty": float(consumed[i]),
               "consumers": [m.nodes[j] for j in m.A.T.tocsr()[i].indices]}
              for i in range(len(m.nodes)) if m.q[i] == 0.0]
    # Presence of leaves is expected -- each must be a genuine purchased input.
    return {"id": 5, "name": "dangling_leaves", "status": "review",
            "count": len(leaves), "share_co2e": 0.0, "leaves": leaves}


def concentration(m, declared, threshold: float) -> dict:
    """Check 7. Where an input error moves the result most, and on what data."""
    e = _model.intensities_dual(m)
    products = {}
    for p in declared:
        idx, x = _model.solve_cone(m, p)
        total = float(m.f_dir[idx] @ x)
        if total == 0.0:
            continue
        nodes, quality = [], {}
        for pos, i in enumerate(idx):
            share = float(x[pos] * m.f_dir[i] / total)
            if share:
                nodes.append({"node": m.nodes[i], "share": share})
                quality[m.dq[i] or "D"] = quality.get(m.dq[i] or "D", 0.0) + share
        edges = []
        for pos, i in enumerate(idx):
            col = m.A[:, i]
            for j, a in zip(col.indices, col.data):
                flow = float(x[pos] * a * e[j] / total)
                if flow >= threshold:
                    edges.append({"from": m.nodes[j], "to": m.nodes[i], "flow_share": flow})
        products[p] = {
            "pcf": total,
            "top_nodes": sorted(nodes, key=lambda d: -d["share"])[:10],
            "material_edges": sorted(edges, key=lambda d: -d["flow_share"]),
            "data_quality": quality,
        }
    return {"id": 7, "name": "concentration_and_data_quality", "status": "review",
            "materiality_threshold": threshold,
            "note": "Node shares partition the footprint. Edge flow shares are a "
                    "routing measure, not a partition: in cyclic networks they "
                    "may sum above one.",
            "products": products}


def run(m, declared, psi=None) -> dict:
    """Full diagnostic profile. Ordered by check id."""
    psi = psi or {}
    tol = psi.get("tolerances", {})
    threshold = psi.get("materiality_threshold", 0.25)

    productivity = cycle_productivity(m)
    checks = [productivity]
    if productivity["status"] == "fail":
        for cid, name in ((1, "solver_residual"), (2, "mass_balance"),
                          (3, "cone_vs_full"), (4, "inventory_reconciliation"),
                          (5, "dangling_leaves"), (7, "concentration_and_data_quality")):
            checks.append({"id": cid, "name": name, "status": "not_evaluated",
                           "reason": "cycle spectral radius >= 1: the Leontief "
                                     "series does not converge"})
    else:
        checks += [
            solver_residual(m, declared, tol.get("solver_residual", 1e-6)),
            mass_balance(m),
            cone_vs_full(m, declared, tol.get("cone_vs_full", 1e-9)),
            inventory_reconciliation(m, declared, psi.get("corporate_inventory_co2e")),
            dangling_leaves(m),
            concentration(m, declared, threshold),
        ]
    checks.sort(key=lambda c: c["id"])
    return {"format": "camf/1.0", "declared_products": list(declared), "checks": checks}


def failed(profile) -> list:
    """Names of checks that did not pass. `review` sections are not failures."""
    return [c["name"] for c in profile["checks"] if c["status"] == "fail"]
