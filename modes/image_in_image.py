"""Mode: PNG secret hidden inside PNG cover. Owner: Sohaila."""

from __future__ import annotations

from pathlib import Path

import cv2

from engine import capacity, crypto, lsb, spread
from preprocessing import image as preprocess_image


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Full image-in-image pipeline. Returns (stego_path, meta).

    Steps:
      1. load cover + secret via preprocessing.image.load_image
      2. serialize_image(secret) -> secret_bytes
      3. check_capacity(cover.shape, b, len(secret_bytes))
      4. seed = key_to_seed(key)
      5. encrypted = xor_bytes(secret_bytes, seed)
      6. stego = lsb.embed(cover, encrypted, b, seed)
      7. cv2.imwrite PNG
      8. return stego_path, meta dict (sidecar schema)

    Caller writes meta to <stego_path>.meta.json.
    
    Args:
        cover_path: Path to cover PNG image.
        secret_path: Path to secret PNG image.
        key: Encryption key (string).
        b: Bit depth [1, 4] for LSB embedding.
    
    Returns:
        (stego_path, meta): tuple of stego file path and metadata dict.
    
    Raises:
        ValueError: If images cannot be loaded or b is invalid.
        CapacityError: If secret is too large for cover.
    """
    # Validate b
    if b not in range(1, 5):
        raise ValueError(f"b must be in [1, 4], got {b}")
    
    # Load images
    cover = preprocess_image.load_image(cover_path)
    secret = preprocess_image.load_image(secret_path)
    
    # Serialize secret image to PNG bytes
    secret_bytes = preprocess_image.serialize_image(secret)
    
    # Check capacity before embedding
    capacity.check_capacity(cover.shape, b, len(secret_bytes))
    
    # Convert key to seed
    seed = spread.key_to_seed(key)
    
    # Encrypt secret bytes with XOR
    encrypted = crypto.xor_bytes(secret_bytes, seed)
    
    # Embed encrypted bytes into cover
    stego = lsb.embed(cover, encrypted, b, seed)
    
    # Write stego to output file
    output_path = str(Path(cover_path).parent / "stego_output.png")
    success = cv2.imwrite(output_path, stego)
    if not success:
        raise ValueError(f"Failed to write stego image to {output_path}")
    
    # Build metadata dict
    meta = {
        "mode": "image_in_image",
        "secret_len": len(secret_bytes),
        "secret_shape": list(secret.shape),
        "secret_dtype": "uint8",
        "b": b,
        "fps": None,
        "frame_count": None,
    }
    
    return output_path, meta


def decode(stego_path: str, key: str, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered secret PNG.

    Args:
        stego_path: Path to stego image file.
        key: Encryption key (same as used in embed).
        meta: Metadata dict from embed (contains secret_len and b).

    Returns:
        Path to recovered secret image PNG file.

    Raises:
        ValueError: If image cannot be loaded or decoding fails.
    """
    b = int(meta["b"])
    # Validate b
    if b not in range(1, 5):
        raise ValueError(f"b must be in [1, 4], got {b}")
    
    # Load stego image
    stego = preprocess_image.load_image(stego_path)
    
    # Convert key to seed (same as embed)
    seed = spread.key_to_seed(key)
    
    # Extract encrypted bytes from stego
    secret_len = meta["secret_len"]
    encrypted = lsb.decode(stego, b, seed, secret_len)
    
    # Decrypt bytes with XOR (same seed)
    secret_bytes = crypto.xor_bytes(encrypted, seed)
    
    # Deserialize bytes back to image
    secret = preprocess_image.deserialize_image(secret_bytes)
    
    # Write recovered secret to output file
    output_path = Path(stego_path).parent / "recovered_secret.png"
    success = cv2.imwrite(str(output_path), secret)
    if not success:
        raise ValueError(f"Failed to write recovered secret to {output_path}")
    
    return str(output_path)
