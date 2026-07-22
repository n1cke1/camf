# CAMF canonicalization (normative)

Version: CAMF-1.0 draft. Test vectors for every rule below live in
`tests/test_canon.py` and `tests/test_merkle.py`.

Semantically identical computation states must produce identical bytes, and
therefore identical hashes. Where a rule below is violated, the cryptographic
identifier stops being an identifier.

## 1. What is hashed

CAMF hashes the **logical content** of each artefact, not the bytes of its
transport file.

This is a deliberate departure from "hash the serialized file". Parquet
writers embed library versions and schema metadata, and CSV admits several
valid quotings of the same field; either would make the package root depend on
the toolchain rather than on the computation. A package written as Parquet and
the same package written as CSV have the same root.

Transport compression is outside the hash boundary.

## 2. Strings

* Unicode normalization form C (NFC).
* UTF-8, no BOM.
* No trailing whitespace; no implicit case folding.

## 3. Numbers

* All numeric values are IEEE-754 binary64.
* `NaN`, `+Inf`, `-Inf` have no canonical form and are rejected.
* `-0.0` is folded onto `0.0` before encoding.
* Integers outside +/-2^53 are rejected, since they are not exactly
  representable and would not survive a round trip.

## 4. Row encoding

A row is the concatenation of its fields **in schema order**. Field order is
part of the schema: reordering columns is a schema change and changes the hash.

| Type | Encoding |
|---|---|
| string | `0x73` + uint32 big-endian byte length + UTF-8 (NFC) bytes |
| float64 | `0x66` + 8 bytes IEEE-754 binary64, big-endian |
| integer | `0x69` + 8 bytes int64, big-endian |
| null | `0x6e` |

Length prefixes are what make the encoding unambiguous: without them
`("ab", "c")` and `("a", "bc")` would collide.

## 5. Row order and identity

* Rows are sorted by the composite key `(plant, product, component, period)`.
* The sort is byte-lexicographic over the NFC UTF-8 encoding of the key
  fields, joined by `0x00`.
* Duplicate keys are an error. A validator rejects the package; it must never
  deduplicate silently, because which duplicate survives would then determine
  the hash.

## 6. JSON objects

`psi.json` and `diagnostics.json` are serialized per RFC 8785 (JSON
Canonicalization Scheme):

* object members sorted by **UTF-16 code units** of the member name, which is
  not the same order as sorting by code points once non-BMP characters appear;
* no insignificant whitespace;
* minimal escaping: `"` `\` and C0 controls, with the short forms
  `\b \t \n \f \r` where they exist, otherwise `\u00xx` in lowercase hex;
* numbers serialized by the ECMAScript `Number::toString` algorithm. Python's
  `repr` switches to exponential notation at different magnitudes than
  ECMAScript does (`1e-5`, `1e17`), so the digits are re-laid-out explicitly.

## 7. Merkle construction

```
leaf(chunk)        = SHA-256(0x00 || chunk)
node(left, right)  = SHA-256(0x01 || left || right)
odd node           promoted unchanged to the next level
file_root          root of the object's tree
package_root       = SHA-256(0x02 || for each object, sorted by name:
                                 uint32(len(name)) || name || file_root)
```

* Tables are chunked at **10 000 rows**; the chunk is the concatenation of the
  encoded rows it contains. Chunk size is normative: changing it changes the
  root.
* JSON objects form a single leaf.
* The odd node is promoted, **not duplicated**. Duplication lets two distinct
  leaf sequences yield one root — with `[a,b,c]` and `[a,b,c,c]` as the
  smallest example.
* The three domain tags `0x00 / 0x01 / 0x02` prevent a leaf, an internal node
  and a package root from ever being confused for one another.
* `manifest.json` carries `package_root` and is therefore not hashed into it.

## 8. Why chunking

Chunking is not a performance device at this scale. It localises a difference
between two reporting periods to a chunk rather than to a whole artefact, so
two packages can be compared structurally without either party revealing the
rows that agree.
