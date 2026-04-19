"""Spread-spectrum pixel ordering. Deterministic from key."""

from __future__ import annotations

import hashlib

import numpy as np


def key_to_seed(key: str) -> int:
    """Return deterministic int seed in [0, 2**31).

    Converts text key to numeric seed via MD5 hash mod 2**31.
    Same key → same seed → same pixel order and XOR keystream on both sides.
    
    MD5 is acceptable here (not for cryptographic hashing) because:
    - We need fast, deterministic uint32 from text string
    - Reversibility is not required (seed is not decryption key)
    - Spread-spectrum diffusion is the primary security layer
    
    Args:
        key: text string (any length, any characters).
    
    Returns:
        seed: int in [0, 2**31) deterministically derived from key.
        
    Examples:
        >>> seed1 = key_to_seed('password123')
        >>> seed2 = key_to_seed('password123')
        >>> assert seed1 == seed2  # Deterministic
        >>> seed3 = key_to_seed('password124')
        >>> assert seed1 != seed3  # Sensitive to input
    """
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**31)


def get_pixel_order(seed: int, total_slots: int) -> np.ndarray:
    """Return permutation of range(total_slots) as int64 ndarray.

    Uses np.random.default_rng(seed).permutation for Fisher-Yates shuffling.
    Ensures embedding spreads across the image/video uniformly, rather than
    sequentially writing to first N pixels (which would be detectable).
    
    Same seed → same permutation (required for decode with same key).
    
    Args:
        seed: RNG seed (from key_to_seed).
        total_slots: number of pixel channel values (H * W * C * frames).
    
    Returns:
        order: int64 array of shape (total_slots,) containing [0, total_slots)
               in random order. Use first N values for N-chunk embedding.
    
    Examples:
        >>> order1 = get_pixel_order(42, 1000)
        >>> order2 = get_pixel_order(42, 1000)
        >>> np.array_equal(order1, order2)  # Deterministic
        True
        >>> set(order1) == set(range(1000))  # Permutation
        True
    """
    return np.random.default_rng(seed).permutation(total_slots)
