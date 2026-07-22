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
psi    (900 bytes) 57fcde11fb9f440fa4f1721bc1b4edb368e4e9d8940728c5dcb8a97bc5b2eacf
```

`package_root` is fixed once `diagnostics.json` is generated — it commits to
the diagnostic profile as well, so it is recorded when the diagnostics module
lands.
