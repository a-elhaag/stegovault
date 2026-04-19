"""XOR stream cipher keyed by seed from engine.spread.key_to_seed.

SECURITY CONTEXT:
This XOR with Numpy PRNG is designed for steganography (obfuscating statistical
patterns in LSBs before embedding) rather than as a standalone encryption cipher.
It provides deterministic, fast bit-scrambling suitable for LSB embedding.

NOT SUITABLE for cryptographic confidentiality without additional layers.
For real encryption, use:
  - AES-CTR (via cryptography.hazmat.primitives.ciphers)
  - ChaCha20 (via cryptography.hazmat.primitives.ciphers)

In StegoVault: XOR is applied BEFORE LSB embedding (by caller) to ensure
embedded bits don't leak plaintext statistical patterns. The steganography
(hiding data in LSBs) + compression format are the primary security layers.
"""

from __future__ import annotations

import numpy as np


def xor_bytes(data: bytes, seed: int) -> bytes:
    """XOR data with keystream from np.random.default_rng(seed).

    Length-preserving. Applied before LSB write (embed) and after LSB read
    (decode) so embedded bits carry no plaintext pattern.
    
    Args:
        data: plaintext bytes to encrypt (or ciphertext to decrypt).
        seed: RNG seed (must be identical for encrypt/decrypt symmetry).
    
    Returns:
        encrypted bytes (same length as input). XOR is self-inverse, so
        xor_bytes(xor_bytes(data, seed), seed) == data.
    
    Examples:
        >>> plaintext = b'hello'
        >>> ciphertext = xor_bytes(plaintext, seed=42)
        >>> recovered = xor_bytes(ciphertext, seed=42)
        >>> assert recovered == plaintext
    """
    rng = np.random.default_rng(seed)
    keystream = np.frombuffer(rng.bytes(len(data)), dtype=np.uint8)
    return (np.frombuffer(data, dtype=np.uint8) ^ keystream).tobytes()
