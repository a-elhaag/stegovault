"""XOR stream cipher keyed by seed from engine.spread.key_to_seed."""

from __future__ import annotations

import numpy as np


def xor_bytes(data: bytes, seed: int) -> bytes:
    """XOR data with keystream from np.random.default_rng(seed).

    Length-preserving. Applied before LSB write (embed) and after LSB read
    (decode) so embedded bits carry no plaintext pattern.
    """
    raise NotImplementedError
