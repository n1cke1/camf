# Licensing

Three kinds of content live in this repository and each carries the licence
that fits what people need to do with it.

| Content | Licence | SPDX | Why |
|---|---|---|---|
| Code — `camf/`, `reproduce.py`, `tests/` | Apache License 2.0 | `Apache-2.0` | Explicit patent grant (§3) and patent-retaliation clause (§3, final paragraph) |
| Specification text — `spec/`, `README.md`, `audit/` | Creative Commons Attribution 4.0 International | `CC-BY-4.0` | Quotable, translatable, includable in regulatory material, with attribution |
| Examples and data — `examples/` | CC0 1.0 Universal | `CC0-1.0` | No one should have to think before running them in a test or a tutorial |

Full texts: [`LICENSE`](LICENSE) (Apache-2.0),
<https://creativecommons.org/licenses/by/4.0/legalcode> (CC BY 4.0),
<https://creativecommons.org/publicdomain/zero/1.0/legalcode> (CC0 1.0).

## Why Apache-2.0 and not MIT

MIT is the right choice for a small developer tool: minimum ceremony, nothing
to think about. CAMF has a different job. It is a specification published
defensively, and the clause that matters here does not exist in MIT — the
express patent licence in §3, together with the retaliation term: anyone who
brings a patent claim over this work loses their licence to it.

That composes with the point of a defensive publication. The publication stops
the disclosed method from being patented by others; Apache-2.0 adds a second
layer, granting every implementer a patent licence from the authors and
contributors, and making an attack on the ecosystem cost the attacker their
own rights. For a format whose value depends on corporate implementers
adopting it without hesitation, this is not decoration: legal review inside
large organisations treats Apache-2.0 markedly more calmly than MIT precisely
because of the patent grant.

The cost is a longer licence and a `NOTICE` file to carry. For a
specification, that is negligible.

## Copyright line and anonymity

Both MIT and Apache require a copyright line, and a name breaks blind review.
The canonical repository carries the real copyright line; the review mirror
derived from it carries `Copyright 2026 Anonymous Author(s)`, with attribution
restored on publication. An anonymous work is fully protected under the Berne
Convention, so nothing is given up by withholding the name for the review
period.

## Publication order

Two requirements pull in opposite directions. A defensive publication wants
the earliest possible public date under the author's name; double-blind review
wants no name near the artefact.

The resolution taken here: **publish the named repository and the archived
release immediately**, so the prior-art date starts running, and give
reviewers the anonymised mirror. A determined reviewer who searches for a
fragment of the code could in principle deanonymise it — this is the
recognised best-effort compromise and editors are familiar with it. The
alternative, keeping everything private until acceptance, would delay the
defensive publication by months, which in a field being actively patented is
the worse trade.
