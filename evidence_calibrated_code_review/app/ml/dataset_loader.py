"""Dataset loading and cleaning for public vulnerability corpora."""
import json
import re
import hashlib
from pathlib import Path


def clean_code_records(records):
    """Clean rows and remove exact or very-near duplicate normalized code."""
    seen, signatures, buckets, cleaned = set(), [], {}, []
    for row in records:
        code = row.get("code") or row.get("func")
        label = row.get("label", row.get("target"))
        if not isinstance(code, str) or len(code.strip()) < 20 or "\x00" in code:
            continue
        try:
            label = int(label)
        except (TypeError, ValueError):
            continue
        if label not in (0, 1):
            continue
        normalized = " ".join(re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]", code))
        digest = hashlib.sha256(normalized.encode("utf-8", "ignore")).hexdigest()
        if digest in seen:
            continue
        # SimHash over token 4-grams; near duplicates at <=3/64 bits are dropped.
        tokens = re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]", normalized)
        shingles = [" ".join(tokens[i:i + 4]) for i in range(max(1, len(tokens) - 3))]
        # Bound the work per function, then calculate bit votes in NumPy instead
        # of a Python loop over every bit of every shingle.
        if len(shingles) > 96:
            step = (len(shingles) - 1) / 95
            shingles = [shingles[round(i * step)] for i in range(96)]
        import numpy as np
        hashes = np.frombuffer(b"".join(hashlib.blake2b(s.encode(), digest_size=8).digest() for s in shingles), dtype=np.uint8)
        bit_counts = np.unpackbits(hashes.reshape(-1, 8), axis=1, bitorder="big").sum(axis=0)
        signature = int.from_bytes(np.packbits(bit_counts >= len(shingles) / 2, bitorder="big").tobytes(), "big")
        candidates = set()
        for band in range(8):
            candidates.update(buckets.get((band, (signature >> (band * 8)) & 255), ()))
        if any((signature ^ signatures[index]).bit_count() <= 3 for index in candidates):
            seen.add(digest)
            continue
        row_index = len(signatures)
        signatures.append(signature)
        for band in range(8):
            buckets.setdefault((band, (signature >> (band * 8)) & 255), []).append(row_index)
        seen.add(digest)
        cleaned.append({"code": code.strip(), "label": label,
                        "group": str(row.get("project") or row.get("repository") or "unknown")})
    return cleaned


def load_jsonl(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def clean_cve_records(records):
    """Keep valid English description/CWE pairs and remove duplicates."""
    seen, output = set(), []
    for row in records:
        text, cwe = row.get("description"), row.get("cwe")
        if not isinstance(text, str) or len(text.strip()) < 20 or not cwe or cwe in {"NVD-CWE-noinfo", "NVD-CWE-Other"}:
            continue
        key = (text.casefold().strip(), cwe)
        if key in seen:
            continue
        seen.add(key)
        output.append({"text": text.strip(), "label": cwe, "cve_id": row.get("cve_id", "")})
    return output
