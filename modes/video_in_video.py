"""Mode: MP4 secret hidden inside MP4 cover. Owner: Youstina."""

from __future__ import annotations

from engine import capacity, crypto, lsb, spread
from preprocessing import video


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Video-in-video pipeline. Returns (stego_mp4_path, meta).

    Steps:
      1. extract_frames for both cover and secret
      2. Serialize all secret frames to bytes
      3. check_capacity(cover_frames[0].shape, b, total_secret_bytes, len(cover_frames))
      4. seed = key_to_seed(key)
      5. xor_bytes on serialized secret
      6. lsb.embed across all cover frames
      7. reconstruct_video
      8. return stego_path, meta (includes secret fps, frame_count, per-frame shape)
    """
    raise NotImplementedError


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered MP4."""
    raise NotImplementedError
