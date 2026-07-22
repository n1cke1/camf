# CAMF-1.0 — Carbon Audit Matrix Format

Draft specification. Status: work in progress.

CAMF is a format for publishing a product carbon footprint together with the
computation that produced it, in a form small enough to hash and cheap enough
to recompute independently.

A CAMF package carries the model — the production network as a table of edges,
the extension vectors, and the assumption set — not the answer. A verifier
rebuilds the matrix from the package, re-solves, and compares against the
declared figures.

## 1. Scope

**In scope.** The mathematical correctness of the published computation: that
the declared footprints follow from the published edge table, extension
vectors and assumptions, and that the package has not been altered since the
commitment was published.

**Out of scope.** That the edge table faithfully represents the production
system; that the emission factors are the right ones; that the underlying ERP
records are accurate. These are verified by other means and carry their own
assurance — attestation makes the final layer transparent, it does not replace
verification of the layers beneath it.

## 2. Normative computation

For a product at node `p` with final demand `y_p`:

```
(I − A) x_p = y_p
PCF_k(p)    = f_kᵀ x_p
```

* `A` (n×n, sparse): `a_ij` is the physical input from node *i* consumed per
  unit of output of node *j*. Column *j* is normalised to the gross output of
  *j*.
* `y_p`: final demand. For a per-unit PCF, the unit vector on `p`.
* `f_k`: extension vector *k*, per unit of node output.

The series `(I − A)⁻¹ = I + A + A² + …` converges when the spectral radius of
`A` is strictly below one (Hawkins–Simon). Cycles — own-use loops, recycling,
by-product loops — are therefore closed analytically in one solve rather than
truncated.

### 2.1 Stored form and the normalisation rule

The package stores the **unnormalised edge table in ERP physical units**, not
`A`. That table is what a verifier reconciles against transaction records;
`A` is derived from it by a fixed rule:

```
row (plant, product = i, component = j, period)
    i ≠ j :  coefficient = c_ij   input j consumed by i, physical units
    i = j :  coefficient = −q_i   gross output of i (negative)

a_ji    = c_ij / q_i        column i of A
f_dir,i = b_i  / q_i        direct intensity of node i
```

`q_i ≤ 0` is an error. A node that consumes inputs but has no diagonal row is
an error. A node that appears only as a component — consumed, never produced —
is an **external leaf**: its column in `A` is empty and its embedded carbon is
zero by construction. Every external leaf must correspond to a genuinely
purchased input; check 5 (§5) enumerates them for exactly this reason.

### 2.2 Cone extraction

Structural extraction and numerical solution are separate steps.

Extraction walks the graph breadth-first against edge direction from `p`,
enumerating the upstream cone `C(p)`. The solve then runs on the restricted
system `(I − A_C) x_p = y_p` by sparse LU factorisation.

The restricted solution is identical to the full-system one, not an
approximation: the cone is closed under predecessors, so every component of
`x` outside it is identically zero. Check 3 (§5) tests this on every run.

Weighting nodes during traversal instead — the tree-shaped alternative —
breaks at the first loop. Solving the full system for every product is correct
but hides which part of the network actually determines a given footprint.

### 2.3 Equivalent dual form

An implementation may solve the intensity (dual) form, in which each row is
the embedded-carbon balance of a node:

```
q_i · f_i − Σ_j c_ij · f_j = b_i     ⇔     (I − Aᵀ) f = f_dir
```

Then `PCF(p) = f_p = f_dirᵀ x_p`, identical to §2. The form of §2 is normative;
the dual is permitted, and the reference implementation checks that both
branches agree to 1e-12.

## 3. Package

```
package/
├── manifest.json      schema version, object inventory, roots, package_root
├── edges.*            edge table (stored form of A and y)
├── factors.*          extension vectors f_k, long format
├── psi.json           assumption set ψ
└── diagnostics.json   diagnostic profile, seven sections
```

`y` is not stored separately when the declaration is per-unit: the demand
vector is the unit vector on each declared product, and the declared products
are listed in the manifest. A non-unit demand is carried as an explicit
`demand` table registered in the manifest.

Transport format is Parquet or CSV; neither affects the hash (see
`canonicalization.md` §1).

## 4. Edge table schema

Field order is normative.

| # | Column | Type | Notes |
|---|---|---|---|
| 1 | plant | str | site code; attribute of the consuming node |
| 2 | product | str | consumer node id, *i* |
| 3 | component | str | input node id, *j*; `i = j` marks the diagonal |
| 4 | period | str | ISO 8601 interval, e.g. `2025-01/2025-12` |
| 5 | unit | str | physical unit of the component |
| 6 | coefficient | float64 | `c_ij`, or `−q_i` on the diagonal |
| 7 | data_quality | enum | `M` measured / `C` calculated / `E` estimated / `D` default |
| 8 | method | str | combustion / mass-balance / CEMS / grid-average |
| 9 | params | str | `NCV=33.5;EF_CO2=56.1;OF=0.995`, keys sorted |
| 10 | emission_formula | str | human-readable formula |
| 11 | co2e | float64 | direct emissions `b_i` (diagonal only) |
| 12–14 | S1, S2, S3 | uint8 | GHG Protocol scope masks |
| 15–16 | CBAM_d, CBAM_i | uint8 | CBAM direct / indirect masks |
| 17 | produced_qty | float64 | `q_i` (diagonal only) |
| 18 | consumed_total | float64 | consumption of *i* by others (diagonal only) |
| 19 | residual | float64 | `produced − consumed` (diagonal only) |
| 20 | legal_entity | str | attribution attribute, not a structural property |

Row identity is `(plant, product, component, period)`, composed from ERP
master data so that any row can be traced back without a side lookup.
Duplicate keys are rejected.

Node identifiers are composite ERP keys and are globally unique across sites.

## 5. Diagnostics

Seven checks, all by-products of the solve rather than additional work. Full
definitions ship with the diagnostics module.

1. **Solver residual** — `‖(I − A) x_p − y_p‖ / ‖y_p‖`, tolerance 1e-6.
2. **Row/column reconciliation** — produced versus consumed per substance,
   within recorded stock movements.
3. **Full-system vs cone** — the two solutions agree to numerical precision.
4. **Corporate inventory reconciliation** — Scope 1 embedded in final output
   against the direct-emissions inventory; the remainder localises to nodes
   that lie in no cone.
5. **Dangling leaves** — consumed but never produced; each is a potential
   understatement and must be a genuine purchased input.
6. **Cycle productivity** — spectral radius of each non-trivial strongly
   connected component, strictly below one; a value at or above one indicates
   double counting or a column-normalisation error.
7. **Contribution concentration and data-quality profile** — edges above the
   materiality threshold, and the `M/C/E/D` distribution weighted by
   contribution.

These complement provenance frameworks such as the pedigree matrix rather than
replacing them: pedigree scores qualify the inputs, these checks verify the
internal consistency of the computation that combines them.

## 6. Attestation

`package_root` is the SHA-256 Merkle root defined in `canonicalization.md` §7.
It is a content address for the computation, which gives three operational
properties:

* **Structural difference between periods** — differing roots localise to the
  objects, and within a table to the chunks, that changed.
* **Exact independent recomputation** — a verifier reproduces the published
  footprint to numerical precision from the package alone.
* **Temporal binding** — a published commitment binds the declarant to the
  computation; retroactive substitution of any input is detectable by anyone
  holding a copy.

Verification of a *published* solution is cheaper than producing it: checking
that `x` satisfies `(I − A) x = y` within tolerance is one sparse
matrix–vector product, linear in the number of non-zeros of `A`.

## 7. Conformance

An implementation conforms if, for any valid package, it:

1. rejects packages violating §2.1, §4 or `canonicalization.md`;
2. derives `A` and `f_dir` by the rule of §2.1;
3. reproduces every declared footprint within the tolerance recorded in ψ;
4. computes a `package_root` equal to the one in the manifest;
5. emits all seven diagnostics of §5.
