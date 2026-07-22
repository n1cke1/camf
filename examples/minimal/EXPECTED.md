# Minimal example — expected values

Five nodes, ten rows, one cycle, one external leaf. Small enough to solve by
hand, which is the point: everything the reference implementation claims is
checkable here without running it.

## Network

```
COAL ──400 t──► PWR ◄──20 Gcal── STM          PWR ⇄ STM is the cycle
                 │ 30 MWh ────────►             (own-use loop)
                 ├──150 MWh──► ALO ──190 t──► ALU
                 └──700 MWh───────────────────►
```

| Node | Output | Direct CO2e | f_dir |
|---|---|---|---|
| PWR | 1 000 MWh | 900 t | 0.9 t/MWh |
| STM | 200 Gcal | 50 t | 0.25 t/Gcal |
| ALO | 200 t | 20 t | 0.1 t/t |
| ALU | 50 t | 10 t | 0.2 t/t |
| COAL | — | — | 0 (external leaf, §5.4 check 5) |

## Hand solution

The cycle is what a tree-shaped rollup cannot close. Here it closes in two
lines:

```
e_PWR = (900 + 20 · e_STM) / 1000 = 0.9 + 0.02 · e_STM
e_STM = (50 + 30 · e_PWR)  / 200  = 0.25 + 0.15 · e_PWR
      ⇒ e_PWR = 0.905 / 0.997
```

Loop gain is 0.02 · 0.15 = 0.003, so the spectral radius of the cycle is
√0.003 ≈ 0.0548 < 1 (Hawkins–Simon, §5.4 check 6).

## Expected results

| Product | PCF, t CO2e / unit | Unit |
|---|---|---|
| PWR | 0.907723169509 | MWh |
| STM | 0.386158475426 | Gcal |
| ALO | 0.780792377131 | t |
| ALU | 15.875135406219 | t |

Solver residual ≤ 2.1e-15 for every product; cone and full-system solutions
agree to machine precision.

## Expected hashes

Canonical roots per `spec/canonicalization.md`:

```
edges  (10 rows)   7b9391f006843ceacdbb963bddf70eb6ad6b0ec95cfd6b749048f7023449087f
psi    (931 bytes) 321b90f45da7b701bd8fbf0ed06489e377ed7c48b8b4979ca638717974b10f9b
package_root       ad711117f6ac75e99d60a1ff8d47777e46d66a0da80870ab074a0b33a75dd1b1
```

`package_root` commits to the diagnostic profile as well as to the edge table
and the assumptions: changing any one of the three changes it.

## Expected diagnostics

```
1. solver_residual                  pass
2. mass_balance                     pass
3. cone_vs_full                     pass
4. inventory_reconciliation         pass     980 t declared, 980 t in matrix
5. dangling_leaves                  review   1: COAL
6. cycle_productivity               pass      ρ = 0.0548
7. concentration_and_data_quality   review
```

Net output is not a mass-balance gap: ALU leaves the system entirely and PWR
is partly exported, both declared in the `residual` column. Check 2 tests the
part that column does *not* explain.

## Defect variants

`examples/defects/` holds the same network with one thing wrong in each, and
each is caught by exactly one check:

| File | Change | Caught by |
|---|---|---|
| `cycle_nonproductive.csv` | PWR draws 8 000 Gcal of steam per 1 000 MWh | 6 — ρ = 1.095, everything downstream reported `not_evaluated` |
| `mass_gap.csv` | alumina output doubled, declared net output untouched | 2 — 50% unexplained |
| `missing_source.csv` | steam combustion under-reported by 30 t | 4 — matrix 950 t against inventory 980 t |
| `dangling.csv` | an alloy input consumed but never produced | 5 — surfaced for review, not a failure |
