"""Mode: PNG secret spread across MP4 cover frames. Owner: Youmna."""

from __future__ import annotations

import tempfile

import cv2
import numpy as np

from engine import capacity, crypto, lsb, spread
from preprocessing import image, video


def _load_secret_image(path: str) -> np.ndarray:
    """Load PNG secret through preprocessing layer with cv2 fallback."""
    try:
        secret = image.load_image(path)
    except NotImplementedError:
        secret = cv2.imread(path, cv2.IMREAD_COLOR)
        if secret is None:
            raise ValueError(f"failed to load image at {path}")

    if secret.dtype != np.uint8 or secret.ndim != 3 or secret.shape[2] != 3:
        raise ValueError(
            f"unexpected secret shape/dtype: {secret.shape}/{secret.dtype} "
            f"(expected (H, W, 3) uint8)"
        )
    return np.ascontiguousarray(secret)


def _serialize_secret(secret: np.ndarray) -> tuple[bytes, dict]:
    """Serialize secret image bytes with metadata."""
    try:
        return image.serialize_image(secret)
    except NotImplementedError:
        secret = np.ascontiguousarray(secret)
        return secret.tobytes(), {
            "shape": list(secret.shape),
            "dtype": str(secret.dtype),
        }


def _deserialize_secret(data: bytes, shape: list[int], dtype: str) -> np.ndarray:
    """Deserialize secret image bytes using preprocessing layer or local fallback."""
    secret_meta = {"shape": shape, "dtype": dtype}
    try:
        secret = image.deserialize_image(data, secret_meta)
    except NotImplementedError:
        arr = np.frombuffer(data, dtype=np.dtype(dtype))
        expected = int(np.prod(shape))
        if arr.size != expected:
            raise ValueError(
                f"secret bytes length mismatch: got {arr.size}, expected {expected}"
            )
        secret = arr.reshape(shape)

    if secret.dtype != np.uint8 or secret.ndim != 3 or secret.shape[2] != 3:
        raise ValueError(
            f"unexpected secret shape/dtype: {secret.shape}/{secret.dtype} "
            f"(expected (H, W, 3) uint8)"
        )
    return np.ascontiguousarray(secret)


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
    cover_frames, fps = video.extract_frames(cover_path)
    secret_img = _load_secret_image(secret_path)
    secret_bytes, secret_meta = _serialize_secret(secret_img)

    capacity.check_capacity(
        cover_shape=cover_frames[0].shape,
        b=b,
        secret_size=len(secret_bytes),
        frame_count=len(cover_frames),
    )

    seed = spread.key_to_seed(key)
    encrypted = crypto.xor_bytes(secret_bytes, seed)

    cover_stack = np.stack(cover_frames, axis=0)
    stego_stack = lsb.embed(cover_stack, encrypted, b, seed)
    # lsb.embed() returns C-contiguous array; convert to list for imageio
    stego_frames = list(stego_stack)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        stego_path = tmp.name
    video.reconstruct_video(stego_frames, stego_path, fps)

    meta = {
        "mode": "image_in_video",
        "secret_len": len(secret_bytes),
        "secret_shape": list(secret_meta["shape"]),
        "secret_dtype": str(secret_meta["dtype"]),
        "b": b,
        "fps": None,
        "frame_count": None,
    }
    return stego_path, meta


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered PNG."""
    for field in ("secret_len", "secret_shape", "secret_dtype"):
        if field not in meta:
            raise ValueError(f"missing required meta field: {field}")

    secret_len = int(meta["secret_len"])
    secret_shape = list(meta["secret_shape"])
    secret_dtype = str(meta["secret_dtype"])

    stego_frames, _ = video.extract_frames(stego_path)
    stego_stack = np.stack(stego_frames, axis=0)

    seed = spread.key_to_seed(key)
    encrypted = lsb.decode(stego_stack, b, seed, secret_len)
    secret_bytes = crypto.xor_bytes(encrypted, seed)
    secret = _deserialize_secret(secret_bytes, secret_shape, secret_dtype)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out_path = tmp.name
    ok = cv2.imwrite(out_path, secret)
    if not ok:
        raise ValueError(f"failed to write decoded image to {out_path}")

    return out_path
