"""Deterministic per-document pseudo-randomness (not real randomness — the
same document must always produce the same design, but two different
documents with the same mood shouldn't render identically)."""

import hashlib


def seed_unit(text: str) -> float:
    h = hashlib.md5(text[:2000].encode("utf-8", errors="ignore")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF
