"""Mode: PNG secret spread across MP4 cover frames. Owner: Youmna."""

from __future__ import annotations

from engine import capacity, crypto, lsb, spread
from preprocessing import image, video


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Image-in-video pipeline. Returns (stego_mp4_path, meta).

    Steps:
      1. extract_frames(cover_path) -> (frames, fps)
      2. serialize_image(secret) -> (secret_bytes, shape_meta)
      3. check_capacity(frames[0].shape, b, len(secret_bytes), len(frames))
      4. seed = key_to_seed(key)
      5. encrypted = xor_bytes(secret_bytes, seed)
      6. Flatten frames to one array, lsb.embed, reshape back
      7. reconstruct_video(stego_frames, output_path, fps)
      8. return stego_path, meta dict
    """
    raise NotImplementedError


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered PNG."""
    raise NotImplementedError
