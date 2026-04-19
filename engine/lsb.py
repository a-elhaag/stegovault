"""Vectorized LSB embed / decode over a shuffled pixel order."""

from __future__ import annotations

import numpy as np


def embed(cover: np.ndarray, secret_bytes: bytes, b: int, seed: int) -> np.ndarray:
    if b not in range(1, 5):
        raise ValueError(f"b must be 1..4, got {b}")

    stego = cover.copy()
    flat = stego.reshape(-1)  # view of all pixel channel values

    # Expand secret bytes to individual bits, MSB first
    secret_arr = np.frombuffer(secret_bytes, dtype=np.uint8)
    bits = np.unpackbits(secret_arr)  # len = len(secret_bytes) * 8

    # Pack bits into b-bit chunks (pad to multiple of b)
    n_chunks = len(secret_bytes) * 8 // b
    # bits already fits exactly: capacity check ensures this upstream
    chunks = bits[: n_chunks * b].reshape(n_chunks, b)
    # Each row is b bits MSB-first → integer value 0..(2^b - 1)
    values = np.packbits(
        np.pad(chunks, ((0, 0), (8 - b, 0)), constant_values=0), axis=1
    ).reshape(n_chunks)

    # Get shuffled pixel slot indices
    from engine.spread import get_pixel_order  # avoid circular at module level
    order = get_pixel_order(seed, flat.size)[:n_chunks]

    # Clear bottom b LSBs of selected slots, then write new values
    mask = np.uint8((0xFF << b) & 0xFF)
    flat[order] = (flat[order] & mask) | values

    return stego


def decode(stego: np.ndarray, b: int, seed: int, secret_len: int) -> bytes:
    if b not in range(1, 5):
        raise ValueError(f"b must be 1..4, got {b}")

    flat = stego.reshape(-1)
    n_chunks = secret_len * 8 // b

    from engine.spread import get_pixel_order
    order = get_pixel_order(seed, flat.size)[:n_chunks]

    # Extract bottom b LSBs
    lsb_mask = np.uint8((1 << b) - 1)
    values = flat[order] & lsb_mask  # shape (n_chunks,)

    # Unpack each value into b bits (MSB-first within b-bit window)
    # Shift values to MSB position in a byte, then unpackbits
    shifted = (values.astype(np.uint8) << (8 - b))
    bits_2d = np.unpackbits(shifted)  # n_chunks * 8 bits, but we want b per chunk
    # Take only the top b bits from each byte-worth
    bits = bits_2d.reshape(n_chunks, 8)[:, :b].reshape(-1)

    # Pack into bytes
    n_bits = secret_len * 8
    bits = bits[:n_bits]
    return np.packbits(bits).tobytes()
