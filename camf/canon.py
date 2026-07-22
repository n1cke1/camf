"""Canonical serialization and Merkle hashing for CAMF packages.

Normative rules: spec/canonicalization.md. Two independent surfaces are
canonicalized here:

  * tabular data -- a typed, length-prefixed row encoding that is hashed
    directly, so the package root does not depend on the transport format
    (Parquet writer version, CSV quoting) at all;
  * JSON objects -- RFC 8785 JSON Canonicalization Scheme.

Both feed one SHA-256 Merkle construction with domain-separated node tags.
"""

from __future__ import annotations

import hashlib
import math
import struct
import unicodedata
from decimal import Decimal

CHUNK_ROWS = 10_000

_LEAF = b"\x00"
_NODE = b"\x01"
_PKG = b"\x02"

_TAG_STR = b"s"
_TAG_F64 = b"f"
_TAG_INT = b"i"
_TAG_NULL = b"n"


# --------------------------------------------------------------------------
# scalars
# --------------------------------------------------------------------------

def nfc(s: str) -> str:
    """Unicode NFC. Every string entering a hash passes through this."""
    return unicodedata.normalize("NFC", s)


def canon_float(x) -> float:
    """float64 in canonical form: finite, with -0.0 folded onto 0.0."""
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"non-finite value has no canonical form: {x!r}")
    return 0.0 if x == 0.0 else x


def js_number(x) -> str:
    """ECMAScript Number::toString, required by RFC 8785 for JSON numbers.

    Python's repr switches to exponential notation at different magnitudes
    than ECMAScript does, so the digits are re-laid-out explicitly.
    """
    x = canon_float(x)
    if x == 0.0:
        return "0"
    if x < 0:
        return "-" + js_number(-x)
    sign, digits, exp = Decimal(repr(x)).normalize().as_tuple()
    s = "".join(map(str, digits))
    k = len(s)
    n = exp + k                       # value == 0.<s> * 10**n
    if k <= n <= 21:
        return s + "0" * (n - k)
    if 0 < n <= 21:
        return s[:n] + "." + s[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + s
    mantissa = s if k == 1 else s[0] + "." + s[1:]
    e = n - 1
    return f"{mantissa}e{'+' if e > 0 else '-'}{abs(e)}"


_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
            "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _json_string(s: str) -> str:
    out = ['"']
    for ch in nfc(s):
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ch < "\x20":
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _jcs(o) -> str:
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, str):
        return _json_string(o)
    if isinstance(o, int):
        if abs(o) > 2 ** 53:
            raise ValueError(f"integer exceeds exact float64 range: {o}")
        return js_number(float(o))
    if isinstance(o, float):
        return js_number(o)
    if isinstance(o, (list, tuple)):
        return "[" + ",".join(_jcs(v) for v in o) + "]"
    if isinstance(o, dict):
        # RFC 8785 sorts member names by UTF-16 code units, not code points.
        items = sorted(((nfc(str(k)), v) for k, v in o.items()),
                       key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(_json_string(k) + ":" + _jcs(v) for k, v in items) + "}"
    raise TypeError(f"not JSON-serializable: {type(o).__name__}")


def jcs(obj) -> bytes:
    """RFC 8785 canonical JSON bytes."""
    return _jcs(obj).encode("utf-8")


# --------------------------------------------------------------------------
# tabular rows
# --------------------------------------------------------------------------

def encode_row(values, types) -> bytes:
    """Typed, length-prefixed encoding of one row.

    Field order is the schema order, never alphabetical: reordering columns
    is a schema change and must change the hash.
    """
    out = []
    for value, kind in zip(values, types):
        if value is None:
            out.append(_TAG_NULL)
        elif kind == "str":
            b = nfc(str(value)).encode("utf-8")
            out.append(_TAG_STR + struct.pack(">I", len(b)) + b)
        elif kind == "f64":
            out.append(_TAG_F64 + struct.pack(">d", canon_float(value)))
        elif kind == "int":
            out.append(_TAG_INT + struct.pack(">q", int(value)))
        else:
            raise ValueError(f"unknown field type: {kind}")
    return b"".join(out)


def sort_key(values, key_positions) -> bytes:
    """Byte-lexicographic ordering key over the composite identifier."""
    return b"\x00".join(nfc(str(values[i])).encode("utf-8") for i in key_positions)


# --------------------------------------------------------------------------
# Merkle
# --------------------------------------------------------------------------

def _h(*parts: bytes) -> bytes:
    m = hashlib.sha256()
    for p in parts:
        m.update(p)
    return m.digest()


def merkle_root(chunks) -> bytes:
    """SHA-256 Merkle root over canonical chunks.

    An odd node is promoted unchanged to the next level rather than being
    duplicated: duplication lets two distinct leaf sequences produce one root.
    """
    chunks = list(chunks) or [b""]
    level = [_h(_LEAF, c) for c in chunks]
    while len(level) > 1:
        nxt = [_h(_NODE, level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def table_root(rows, chunk_rows: int = CHUNK_ROWS) -> bytes:
    """Merkle root of an encoded, already-sorted row sequence."""
    rows = list(rows)
    chunks = [b"".join(rows[i:i + chunk_rows]) for i in range(0, len(rows), chunk_rows)]
    return merkle_root(chunks)


def blob_root(data: bytes) -> bytes:
    """Merkle root of a single-object artefact (psi.json, diagnostics.json)."""
    return merkle_root([data])


def package_root(roots: dict) -> bytes:
    """Root over the whole package, bound to logical object names."""
    parts = []
    for name in sorted(roots, key=lambda n: nfc(n).encode("utf-8")):
        nb = nfc(name).encode("utf-8")
        parts += [struct.pack(">I", len(nb)), nb, roots[name]]
    return _h(_PKG, b"".join(parts))


def hexroot(root: bytes) -> str:
    return root.hex()
