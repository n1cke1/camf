"""Assembly of the attestable package {A, y, f_k, psi} and its manifest.

The manifest carries the package root and is therefore not itself hashed into
it. Everything else in the package is.
"""

from __future__ import annotations

from . import canon
from .model import KEY_POSITIONS, TYPES


def table_object(rows, types=TYPES, key_positions=KEY_POSITIONS):
    """Sort rows canonically, encode them, return (encoded rows, root)."""
    ordered = sorted(rows, key=lambda r: canon.sort_key(r, key_positions))
    seen = set()
    for r in ordered:
        k = canon.sort_key(r, key_positions)
        if k in seen:
            raise ValueError(f"duplicate composite key: {k!r}")
        seen.add(k)
    encoded = [canon.encode_row(r, types) for r in ordered]
    return encoded, canon.table_root(encoded)


def build_package(edges, psi, diagnostics, factors=None):
    """Return (manifest, roots) for the given artefacts."""
    objects, roots = [], {}

    encoded, root = table_object(edges)
    roots["edges"] = root
    objects.append({"name": "edges", "role": "A,y", "kind": "table",
                    "rows": len(encoded), "root": canon.hexroot(root)})

    if factors is not None:
        encoded_f, root_f = table_object(*factors)
        roots["factors"] = root_f
        objects.append({"name": "factors", "role": "f_k", "kind": "table",
                        "rows": len(encoded_f), "root": canon.hexroot(root_f)})

    for name, role, obj in (("psi", "psi", psi), ("diagnostics", "profile", diagnostics)):
        blob = canon.jcs(obj)
        roots[name] = canon.blob_root(blob)
        objects.append({"name": name, "role": role, "kind": "json",
                        "bytes": len(blob), "root": canon.hexroot(roots[name])})

    manifest = {
        "format": "camf/1.0",
        "hash_algorithm": "SHA-256",
        "merkle": {"chunk_rows": canon.CHUNK_ROWS, "odd_node": "promote"},
        "objects": sorted(objects, key=lambda o: o["name"]),
        "package_root": canon.hexroot(canon.package_root(roots)),
    }
    return manifest, roots
