# Auditor checklist

For an engagement verifying a product carbon footprint published as a CAMF
package. Part A runs in seconds on a laptop and needs nothing but the package.
Part B is the part that requires an auditor: it cannot be automated, and
passing Part A without it establishes nothing about the real world.

Record the package root you examined. Every finding below refers to it.

```
package_root  ____________________________________________________________
period        ______________________   declarant  ________________________
```

## A. Package integrity and mathematics

Run `python reproduce.py --verify <package>` and confirm each line.

- [ ] **A1. Commitment matches.** The recomputed `package_root` equals the one
      published in the declaration. A mismatch ends the engagement: the
      artefact is not the one that was committed to.
- [ ] **A2. Schema valid.** `manifest.json` validates against
      `spec/package.schema.json`, `psi.json` against `spec/psi.schema.json`.
- [ ] **A3. Canonical form.** Rows are sorted by `(plant, product, component,
      period)`, no duplicate keys, no `NaN`/`±Inf`/`−0.0`.
- [ ] **A4. Matrix derivation.** `A` and `f_dir` follow the normalisation rule
      of the specification §2.1; every node with inputs has a diagonal row and
      strictly positive output.
- [ ] **A5. Declared footprints reproduce** within the tolerance recorded in ψ.
- [ ] **A6. Residual** below tolerance for every declared product.
- [ ] **A7. Cone equals full system** to numerical precision.
- [ ] **A8. Scope masks sum** to the declared total per product; no negative
      footprint.
- [ ] **A9. Cycle productivity.** Every strongly connected component has
      spectral radius below one. A value at or above one is not a rounding
      issue: it means a self-reproducing material flow, and in practice double
      counting or a normalisation error.

## B. Substantive work at the declarant

These test whether the model describes the plant. Nothing in Part A can.

- [ ] **B1. Sample the concentrated edges.** Take the edges flagged by check 7
      — they are where an input error moves the answer most — and reconcile
      `coefficient` and `produced_qty` against ERP transactions for the period.
      Record sample size and deviations.
- [ ] **B2. Direct emissions.** Reconcile `co2e` on sampled diagonal rows
      against the emissions inventory, CEMS records or fuel accounts.
- [ ] **B3. Corporate inventory.** Confirm the figure in
      `corporate_inventory_co2e` is the externally reported one, and that the
      gap reported by check 4 is explained rather than assumed.
- [ ] **B4. Data quality labels.** For rows marked `M`, obtain the measurement
      records. A label of `M` without a measurement protocol is a
      misstatement, not a formality.
- [ ] **B5. Dangling leaves.** Check 5 lists every input the model treats as
      having zero embedded carbon. Confirm each is a genuinely purchased
      external input. Any internally produced material appearing here is an
      understatement of the footprint.
- [ ] **B6. Mass balance gaps.** For each gap reported by check 2, obtain the
      stock movement or loss that explains it.
- [ ] **B7. Emission factors.** Each entry in ψ carries a source and version.
      Confirm they are the cited ones and that the GWP set matches the
      reporting requirement.
- [ ] **B8. Scope and CBAM boundaries.** Obtain the legal basis for the Scope 1
      boundary and for the CBAM direct/indirect masks.
- [ ] **B9. Route inventory.** Confirm that the nodes are the technological
      routes they claim to be, defined by documented composite keys from ERP
      master data.
- [ ] **B10. Period alignment.** The period matches the financial reporting
      cycle relied upon for the underlying records.

## C. What this engagement does not cover

State these explicitly in the opinion rather than leaving them implied.

- The package root attests the computation, not the plant.
- Assurance over the underlying transaction records derives from the financial
  audit of the ERP environment, not from this engagement, unless separately
  performed.
- Upstream embedded carbon (`f4`) inherits the quality of supplier
  disclosures and is no better than they are.
- Checks 5 and 7 are review sections: they report, they do not pass or fail.
