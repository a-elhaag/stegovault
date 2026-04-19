"""Spread-spectrum pixel ordering. Deterministic from key."""

from __future__ import annotations

import hashlib

import numpy as np


def key_to_seed(key: str) -> int:
    """Return deterministic int seed in [0, 2**31).

    md5(key) mod 2**31 as mandated by README.
    Same key -> same seed -> same pixel order and XOR keystream on both sides.
    """
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31)


def get_pixel_order(seed: int, total_slots: int) -> np.ndarray:
    """Return permutation of range(total_slots) as int64 ndarray.

    Uses np.random.default_rng(seed).permutation.
    total_slots = H * W * C * frame_count for the cover.
    """
    return np.random.default_rng(seed).permutation(total_slots)
