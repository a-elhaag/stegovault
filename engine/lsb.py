"""Vectorized LSB embed / decode over a shuffled pixel order."""

from __future__ import annotations

import numpy as np


def embed(cover: np.ndarray, secret_bytes: bytes, b: int, seed: int) -> np.ndarray:
    """Return stego copy of cover with secret bits in bottom b LSBs.

    cover: (H, W, 3) uint8 — or pre-flattened multi-frame array.
    secret_bytes: already XOR-encrypted by engine.crypto.xor_bytes.
    b: 1..4 — LSBs overwritten per pixel channel.
    seed: from engine.spread.key_to_seed — drives pixel permutation.

    Fully vectorized (numpy). No Python loops over pixels.
    Raises ValueError if b not in 1..4.
    """
    raise NotImplementedError


def decode(stego: np.ndarray, b: int, seed: int, secret_len: int) -> bytes:
    """Return XOR-encrypted secret bytes (caller applies un-XOR).

    Inverse of embed. Reproduces the same shuffled order via seed,
    extracts bottom b LSBs, packs into secret_len bytes.
    """
    raise NotImplementedError
