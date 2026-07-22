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

## Try it

```bash
pip install -e ".[test]"
python reproduce.py                    # build a package, hash it, report
python reproduce.py --verify package   # recompute and compare
pytest -q
```

```
nodes 5   edges 10   declared 1
package_root  ad711117f6ac75e99d60a1ff8d47777e46d66a0da80870ab074a0b33a75dd1b1

products
  ALU         15.875135406219  t CO2e / t

diagnostics
  1. solver_residual                  pass
  2. mass_balance                     pass
  3. cone_vs_full                     pass
  4. inventory_reconciliation         pass
  5. dangling_leaves                  review
  6. cycle_productivity               pass
  7. concentration_and_data_quality   review
```

## What is here

| | |
|---|---|
| `spec/CAMF-1.0.md` | format and computation, normative |
| `spec/canonicalization.md` | byte-level rules and the Merkle construction |
| `spec/package.schema.json`, `spec/psi.schema.json` | validated in CI |
| `camf/canon.py` | canonical encoding, RFC 8785 JCS, SHA-256 Merkle |
| `camf/model.py` | edge table → `A`, upstream cone, sparse LU |
| `camf/diagnostics.py` | the seven checks |
| `camf/package.py` | package assembly and manifest |
| `reproduce.py` | build and verify, end to end |
| `examples/minimal/` | five nodes, one cycle, solvable by hand |
| `examples/defects/` | the same network with one thing wrong in each |

Under 500 lines of code, with another 320 of tests. That is the point: a
reviewer can read all of it, which is worth more than a large implementation
nobody will ever see.

The minimal example needs no execution to check —
`examples/minimal/EXPECTED.md` carries the hand solution, the expected
footprints, the diagnostic profile and the frozen canonical roots. The cycle
in it (electricity ⇄ steam) is the case a tree-shaped rollup has to truncate;
here it closes in one solve.

Each file in `examples/defects/` breaks exactly one check, and the test suite
asserts that the other six stay quiet.

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

## Licensing

Three kinds of content, three licences — see [LICENSES.md](LICENSES.md) for
the reasoning.

| Content | Licence |
|---|---|
| Code (`camf/`, `reproduce.py`, `tests/`) | Apache-2.0 — for the express patent grant and the retaliation clause |
| Specification text (`spec/`, `README.md`, `audit/`) | CC BY 4.0 — quotable, translatable, includable in regulatory material |
| Examples and data (`examples/`) | CC0 1.0 — nobody should have to think before running them |

The anonymised copy used for double-blind review is produced by
`tools/anonymize.sh`; it carries `Anonymous Author(s)` as the copyright line,
and attribution is restored on publication.
