# CAMF — Carbon Audit Matrix Format

A product carbon footprint is usually published as a number. CAMF publishes
the computation that produced it: the production network as a table of edges,
the extension vectors, and the assumption set — small enough to hash, cheap
enough for anyone to recompute.

```
(I − A) x_p = y_p        PCF_k(p) = f_kᵀ x_p
```

Cycles — own-use loops, recycling, by-product loops — close analytically in
one solve instead of being truncated. Allocation is endogenous: each node's
material balance is taken as recorded rather than reconstructed by a
methodological choice. Verification therefore moves from re-testing individual
products to testing the rules that build `A` and `f`, and a canonical
serialization makes the result cryptographically attestable.

## Status

Work in progress. Specification and core are in place; the synthetic data
generator, the diagnostics module and the end-to-end `reproduce.py` are not
yet written.

| | |
|---|---|
| `spec/CAMF-1.0.md` | format and computation, normative |
| `spec/canonicalization.md` | byte-level rules and the Merkle construction |
| `spec/package.schema.json`, `spec/psi.schema.json` | validated in CI |
| `camf/canon.py` | canonical encoding, RFC 8785 JCS, SHA-256 Merkle |
| `camf/model.py` | edge table → `A`, upstream cone, sparse LU |
| `camf/package.py` | package assembly and manifest |
| `examples/minimal/` | five nodes, one cycle, solvable by hand |

## Try it

```bash
pip install -e ".[test]"
pytest -q
```

The minimal example is small enough to check without running anything —
`examples/minimal/EXPECTED.md` carries the hand solution, the expected
footprints and the frozen canonical roots.

```python
from camf import model

m = model.build(model.read_edges_csv("examples/minimal/edges.csv"))
model.pcf(m, "ALU")        # 15.875135406219
model.residual(m, "ALU")   # 2.1e-15
```

## What attestation does and does not do

The package root verifies that the declared footprints follow from the
published edge table, vectors and assumptions, and that nothing has been
altered since the commitment was published.

It does not verify that the edge table represents the production system, that
the emission factors are the right ones, or that the underlying records are
accurate. Those carry their own assurance. Attestation makes the final layer
transparent; it does not replace verification of the layers beneath it.

## Data

Every example and test in this repository runs on synthetic data. No
enterprise data is present, and none is required to reproduce anything
published here.

## License

Apache-2.0.
