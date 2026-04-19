"""Mode: PNG secret hidden inside PNG cover. Owner: Sohaila."""

from __future__ import annotations

from engine import capacity, crypto, lsb, spread
from preprocessing import image


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Full image-in-image pipeline. Returns (stego_path, meta).

    Steps:
      1. load cover + secret via preprocessing.image.load_image
      2. serialize_image(secret) -> (secret_bytes, shape_meta)
      3. check_capacity(cover.shape, b, len(secret_bytes))
      4. seed = key_to_seed(key)
      5. encrypted = xor_bytes(secret_bytes, seed)
      6. stego = lsb.embed(cover, encrypted, b, seed)
      7. cv2.imwrite PNG
      8. return stego_path, meta dict (sidecar schema)

    Caller writes meta to <stego_path>.meta.json.
    """
    raise NotImplementedError


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered secret PNG."""
    raise NotImplementedError
