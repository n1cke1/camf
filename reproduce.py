"""Build a CAMF package, hash it, and verify it — end to end, one command.

    python reproduce.py                      # build from examples/minimal
    python reproduce.py --verify package/    # recompute and compare
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from camf import canon, diagnostics, model, package

HERE = Path(__file__).resolve().parent
DEFAULTS = HERE / "examples" / "minimal"


def build(edges_path, psi_path, declared, out: Path) -> dict:
    t0 = time.perf_counter()
    rows = model.read_edges_csv(edges_path)
    psi = json.loads(Path(psi_path).read_text(encoding="utf-8"))
    m = model.build(rows)
    t_build = time.perf_counter() - t0

    t0 = time.perf_counter()
    profile = diagnostics.run(m, declared, psi)
    t_diag = time.perf_counter() - t0

    t0 = time.perf_counter()
    manifest, _ = package.build_package(rows, psi, profile)
    t_hash = time.perf_counter() - t0

    manifest["period"] = psi.get("period", "")
    manifest["products"] = [{"code": p, "unit": m.unit[m.index[p]],
                             "pcf": model.pcf(m, p)} for p in declared]

    out.mkdir(parents=True, exist_ok=True)
    ordered, _ = package.table_object(rows)  # canonical order for the transport file
    with open(out / "edges.csv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(",".join(model.COLUMNS) + "\n")
        for r in sorted(rows, key=lambda r: canon.sort_key(r, model.KEY_POSITIONS)):
            fh.write(",".join("" if v is None else
                              canon.js_number(v) if isinstance(v, float) else str(v)
                              for v in r) + "\n")
    (out / "psi.json").write_bytes(canon.jcs(psi))
    (out / "diagnostics.json").write_bytes(canon.jcs(profile))
    (out / "manifest.json").write_bytes(canon.jcs(manifest))

    report(m, manifest, profile, declared, {"build": t_build, "diagnostics": t_diag,
                                            "hash": t_hash, "rows": len(ordered)})
    return manifest


def report(m, manifest, profile, declared, timing):
    print(f"nodes {len(m.nodes)}   edges {timing['rows']}   declared {len(declared)}")
    print(f"package_root  {manifest['package_root']}")
    print("\nproducts")
    for p in manifest["products"]:
        print(f"  {p['code']:8s} {p['pcf']:>18.12f}  t CO2e / {p['unit']}")
    print("\ndiagnostics")
    for c in profile["checks"]:
        print(f"  {c['id']}. {c['name']:32s} {c['status']}")
    print(f"\ntiming  build {timing['build']*1000:.1f} ms   "
          f"diagnostics {timing['diagnostics']*1000:.1f} ms   "
          f"hash {timing['hash']*1000:.1f} ms")


def verify(pkg: Path) -> int:
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    psi = json.loads((pkg / "psi.json").read_text(encoding="utf-8"))
    rows = model.read_edges_csv(pkg / "edges.csv")
    m = model.build(rows)
    declared = [p["code"] for p in manifest.get("products", [])]

    profile = diagnostics.run(m, declared, psi)
    recomputed, _ = package.build_package(rows, psi, profile)
    root_ok = recomputed["package_root"] == manifest["package_root"]

    tol = psi.get("tolerances", {}).get("declared_pcf", 1e-6)
    mismatches = [p["code"] for p in manifest.get("products", [])
                  if abs(model.pcf(m, p["code"]) - p["pcf"]) > tol * max(1.0, abs(p["pcf"]))]
    failed = diagnostics.failed(profile)

    print(f"package_root   {'match' if root_ok else 'MISMATCH'}")
    print(f"declared PCF   {'match' if not mismatches else 'MISMATCH: ' + ', '.join(mismatches)}")
    print(f"diagnostics    {'all pass' if not failed else 'failed: ' + ', '.join(failed)}")
    return 0 if root_ok and not mismatches and not failed else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges", default=DEFAULTS / "edges.csv")
    ap.add_argument("--psi", default=DEFAULTS / "psi.json")
    ap.add_argument("--declare", nargs="+", default=["ALU"])
    ap.add_argument("--out", type=Path, default=HERE / "package")
    ap.add_argument("--verify", type=Path)
    args = ap.parse_args(argv)
    if args.verify:
        return verify(args.verify)
    build(args.edges, args.psi, args.declare, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
