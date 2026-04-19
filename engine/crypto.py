"""XOR stream cipher keyed by seed from engine.spread.key_to_seed."""

from __future__ import annotations

import numpy as np


def xor_bytes(data: bytes, seed: int) -> bytes:
    """XOR data with keystream from np.random.default_rng(seed).

    Length-preserving. Applied before LSB write (embed) and after LSB read
    (decode) so embedded bits carry no plaintext pattern.
    """
    rng = np.random.default_rng(seed)
    keystream = rng.integers(0, 256, size=len(data), dtype=np.uint8)
    return bytes(np.frombuffer(data, dtype=np.uint8) ^ keystream)
