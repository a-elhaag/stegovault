from __future__ import annotations

import numpy as np

from engine.spread import get_pixel_order


def embed(cover: np.ndarray, secret_bytes: bytes, b: int, seed: int, inplace: bool = False) -> np.ndarray:
    """Embed secret_bytes in LSBs of cover using spread-spectrum ordering.
    
    Replaces the bottom b bits of randomly-ordered (seeded) pixel channels
    with secret bits. Uses XOR encryption (applied by caller) to avoid plaintext
    pattern leakage.
    
    Args:
        cover: (H, W, C) or (frames, H, W, C) uint8 array. Will not be modified
               unless inplace=True.
        secret_bytes: serialized secret data to embed (bytes).
        b: bit depth in [1, 4]. More bits = higher capacity but more visible noise.
        seed: RNG seed for deterministic pixel ordering (from key_to_seed).
        inplace: if True, modify cover array directly (no copy). Use only if cover
                 is temporary/working array. Default False preserves input.
    
    Returns:
        stego: uint8 array with embedded secret (same shape as cover).
               Always C-contiguous for safe use with cv2/imageio.
    
    Raises:
        ValueError: if b not in [1, 4] or arrays have unexpected dtype.
    
    Examples:
        >>> cover = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        >>> secret = b'hello world'
        >>> stego = embed(cover, secret, b=2, seed=42)
        >>> assert stego.shape == cover.shape
        >>> assert stego.dtype == np.uint8
        
    Performance Note:
        - Default behavior (inplace=False): creates 1× copy of cover.
          Peak memory = 2× cover size during operation.
        - With inplace=True: modifies cover directly, no copy.
          Peak memory = 1× cover size (for large videos: saves ~6 MB per 1080p frame).
    """
    if b not in range(1, 5):
        raise ValueError(f"b must be 1..4, got {b}")

    stego = cover if inplace else cover.copy()
    flat = stego.reshape(-1)  # view of all pixel channel values

    # Expand secret bytes to individual bits, MSB first
    secret_arr = np.frombuffer(secret_bytes, dtype=np.uint8)
    bits = np.unpackbits(secret_arr)  # len = len(secret_bytes) * 8

    # Pack bits into b-bit chunks (pad end with 0s if not multiple of b)
    n_bits = len(secret_bytes) * 8
    n_chunks = (n_bits + b - 1) // b
    
    if n_bits % b != 0:
        bits = np.pad(bits, (0, n_chunks * b - n_bits), constant_values=0)
        
    chunks = bits.reshape(n_chunks, b)
    # Each row is b bits MSB-first → integer value 0..(2^b - 1)
    values = np.packbits(
        np.pad(chunks, ((0, 0), (8 - b, 0)), constant_values=0), axis=1
    ).reshape(n_chunks)

    # Get shuffled pixel slot indices
    order = get_pixel_order(seed, flat.size)[:n_chunks]

    # Clear bottom b LSBs of selected slots, then write new values
    mask = np.uint8((0xFF << b) & 0xFF)
    flat[order] = (flat[order] & mask) | values

    return stego


def decode(stego: np.ndarray, b: int, seed: int, secret_len: int) -> bytes:
    """Extract secret bytes from LSBs of stego (inverse of embed).
    
    Reads the bottom b bits of randomly-ordered (seeded) pixel channels,
    unpacks them to bytes, and returns encrypted secret. Caller must XOR
    with same seed to recover plaintext.
    
    Args:
        stego: (H, W, C) or (frames, H, W, C) uint8 array with embedded secret.
        b: bit depth used during embedding [1, 4].
        seed: RNG seed used during embedding (must be identical).
        secret_len: byte length of embedded secret (must be accurate).
    
    Returns:
        secret_bytes: encrypted bytes extracted from LSBs (length = secret_len).
                      Still encrypted; caller must xor_bytes(result, seed) to decrypt.
    
    Raises:
        ValueError: if b not in [1, 4] or array has unexpected dtype.
    
    Examples:
        >>> stego = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        >>> secret = b'hello world'
        >>> encrypted = decode(stego, b=2, seed=42, secret_len=len(secret))
        >>> assert len(encrypted) == len(secret)
    """
    if b not in range(1, 5):
        raise ValueError(f"b must be 1..4, got {b}")

    flat = stego.reshape(-1)
    n_bits = secret_len * 8
    n_chunks = (n_bits + b - 1) // b

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
    bits = bits[:n_bits]
    return np.packbits(bits).tobytes()
