#!/usr/bin/env python3
"""Validate codec files against the spec grammar and replay their test vectors.

Reference implementation of the decode-table grammar used by the Awaro gateway
firmware (lns_codec): field:type@offset[/div][#unit], big-endian types
u8 i8 u16 i16 u24 u32 i32 f32, 'l' suffix for little-endian multi-byte types.

Usage:
    python tools/validate.py                 # validate the whole database
    python tools/validate.py path/to/x.json  # validate specific files
"""
import json
import math
import re
import struct
import sys
from pathlib import Path

MAX_NAME = 23     # LNS_CODEC_NAME_LEN - 1
MAX_SPEC = 160    # LNS_CODEC_SPEC_LEN
MAX_FIELDS = 24   # LNS_CODEC_MAX_FIELDS

FIELD_RE = re.compile(
    r"^([A-Za-z0-9_]+):(u8|i8|u16l?|i16l?|u24|u32l?|i32l?|f32l?)"
    r"@([0-9]+)(?:/([0-9]+(?:\.[0-9]+)?))?(?:#([^ ;]+))?$"
)
SIZES = {"u8": 1, "i8": 1, "u16": 2, "i16": 2, "u24": 3, "u32": 4, "i32": 4, "f32": 4}


def parse_spec(spec):
    """Return a list of (name, type, offset, div, unit). Raise ValueError on bad input."""
    if len(spec) > MAX_SPEC:
        raise ValueError(f"spec is {len(spec)} chars (gateway limit {MAX_SPEC})")
    fields = []
    for tok in re.split(r"[ ;]+", spec.strip()):
        if not tok:
            continue
        m = FIELD_RE.match(tok)
        if not m:
            raise ValueError(f"bad field syntax: {tok!r}")
        name, typ, off, div, unit = m.groups()
        fields.append((name, typ, int(off), float(div) if div else 1.0, unit or ""))
    if not fields:
        raise ValueError("spec has no fields")
    if len(fields) > MAX_FIELDS:
        raise ValueError(f"{len(fields)} fields (gateway limit {MAX_FIELDS})")
    return fields


def decode(fields, payload):
    """Decode a bytes payload with a parsed spec. Fields beyond the frame are skipped."""
    out = {}
    for name, typ, off, div, _unit in fields:
        le = typ.endswith("l")
        base = typ[:-1] if le else typ
        size = SIZES[base]
        if off + size > len(payload):
            continue
        chunk = payload[off:off + size]
        if base == "f32":
            val = struct.unpack("<f" if le else ">f", chunk)[0]
        else:
            val = int.from_bytes(chunk, "little" if le else "big",
                                 signed=base.startswith("i"))
        out[name] = val / div
    return out


def check_file(path):
    errors = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"invalid JSON: {e}"]

    for key in ("vendor", "model", "name", "spec", "tests"):
        if key not in doc:
            errors.append(f"missing required field {key!r}")
    if errors:
        return errors

    name = doc["name"]
    if not re.fullmatch(r"[a-z0-9_-]+", name):
        errors.append(f"name {name!r} must be [a-z0-9_-]")
    if len(name) > MAX_NAME:
        errors.append(f"name {name!r} is {len(name)} chars (gateway limit {MAX_NAME})")
    if path.parent.name not in ("example",) and doc["vendor"] != path.parent.name:
        errors.append(f"vendor {doc['vendor']!r} does not match directory {path.parent.name!r}")

    try:
        fields = parse_spec(doc["spec"])
    except ValueError as e:
        return errors + [f"spec: {e}"]

    if not doc["tests"]:
        errors.append("at least one test vector is required")
    for i, t in enumerate(doc["tests"]):
        label = f"tests[{i}]"
        hexstr = re.sub(r"\s+", "", t.get("payload", ""))
        if not hexstr or len(hexstr) % 2 or not re.fullmatch(r"[0-9A-Fa-f]+", hexstr):
            errors.append(f"{label}: payload must be a non-empty even-length hex string")
            continue
        got = decode(fields, bytes.fromhex(hexstr))
        for k, exp in (t.get("expect") or {}).items():
            if k not in got:
                errors.append(f"{label}: expected field {k!r} not produced "
                              f"(decoded: {sorted(got)})")
            elif not math.isclose(got[k], exp, rel_tol=1e-6, abs_tol=1e-6):
                errors.append(f"{label}: {k} = {got[k]!r}, expected {exp!r}")
    return errors


def main(argv):
    root = Path(__file__).resolve().parent.parent
    paths = ([Path(a) for a in argv]
             if argv else sorted((root / "codecs").rglob("*.json")))
    failed = 0
    for p in paths:
        errs = check_file(p)
        rel = p.relative_to(root) if p.is_relative_to(root) else p
        if errs:
            failed += 1
            print(f"FAIL {rel}")
            for e in errs:
                print(f"     - {e}")
        else:
            print(f"ok   {rel}")
    print(f"\n{len(paths)} codec file(s), {failed} failing")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
