# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions refer to the specification; the reference implementation tracks it.

## [Unreleased]

### Added
- CAMF-1.0 draft specification: normative computation, edge table schema,
  package layout, conformance criteria.
- Canonicalization rules with test vectors: NFC, float64 handling, RFC 8785
  JCS, typed row encoding, SHA-256 Merkle construction.
- JSON Schemas for the manifest and for the assumption set ψ, validated in CI.
- Reference implementation: canonical encoding, edge table to technology
  matrix, upstream cone extraction, sparse LU solve, the seven diagnostics,
  package assembly, end-to-end `reproduce.py`.
- `examples/minimal` — five nodes, one cycle, one external leaf, solvable by
  hand, with expected footprints and frozen canonical roots.
- `examples/defects` — four variants, each caught by exactly one check.
- Auditor checklist and opinion template.
- `tools/anonymize.sh` — derives the double-blind review mirror from the named
  repository.

### Decisions worth recording

- **Hash logical content, not file bytes.** Parquet writers embed library
  versions and schema metadata; CSV admits several valid quotings of one
  field. Hashing the file would make the package root depend on the toolchain
  rather than on the computation. A package written as Parquet and the same
  package written as CSV now produce one root.
- **Check 2 tests the unexplained gap, not the raw difference.** Net output is
  legitimate — a final product leaves the system entirely, electricity may be
  sold — and the declarant records that in the `residual` column. Comparing
  produced against consumed directly failed on a correct example.
- **Check 4 reaches outside the package.** Reconciling embedded Scope 1
  against the matrix's own direct emissions is an algebraic identity and tests
  nothing. The check compares against the externally reported corporate
  inventory; without that figure it reports `not_evaluated` rather than pass.
- **Merkle promotes the odd node instead of duplicating it.** Duplication
  lets `[a,b,c]` and `[a,b,c,c]` produce the same root.
- **A non-productive cycle stops the profile.** With spectral radius at or
  above one the Leontief series diverges, so the remaining checks report
  `not_evaluated` rather than plausible numbers.
- **Split licensing.** Apache-2.0 for code (patent grant and retaliation),
  CC BY 4.0 for the specification text, CC0 for examples.
