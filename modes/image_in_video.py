"""Mode: PNG secret spread across video cover frames. Owner: Youmna."""

from __future__ import annotations

import math
import tempfile
import collections.abc

import cv2
import imageio.v3 as iio
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
    """Serialize secret as raw bytes with shape/dtype metadata.

    Raw bytes are resilient to partial corruption in lossy video codecs: decode can
    still recover an image tensor (possibly noisy) instead of hard-failing on PNG
    container/header corruption.
    """
    secret = np.ascontiguousarray(secret)
    return secret.tobytes(), {
        "shape": list(secret.shape),
        "dtype": str(secret.dtype),
    }


def _deserialize_secret(data: bytes, shape: list[int], dtype: str) -> np.ndarray:
    """Deserialize secret bytes with backward compatibility.

    New payloads are raw bytes. Legacy payloads may be PNG bytes from earlier
    builds; those are decoded through preprocessing.image.deserialize_image.
    """
    dt = np.dtype(dtype)
    expected_bytes = int(np.prod(shape)) * dt.itemsize

    if len(data) == expected_bytes:
        arr = np.frombuffer(data, dtype=dt)
        secret = arr.reshape(shape)
    else:
        secret_meta = {"shape": shape, "dtype": dtype}
        try:
            secret = image.deserialize_image(data, secret_meta)
        except Exception as exc:
            raise ValueError(
                "failed to decode secret bytes: expected raw image bytes or valid PNG payload"
            ) from exc

    if secret.dtype != np.uint8 or secret.ndim != 3 or secret.shape[2] != 3:
        raise ValueError(
            f"unexpected secret shape/dtype: {secret.shape}/{secret.dtype} "
            f"(expected (H, W, 3) uint8)"
        )
    return np.ascontiguousarray(secret)


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Image-in-video pipeline. Returns (stego_video_path, meta).

    Optimized for Streamlit constraints:
    We probe the video to check dimensions, calculate exact frames needed
    for the secret capacity, extract *only* those frames to a numpy stack,
    embed the hidden data, then reconstruct the video via a generator which
    yields the modified frames followed by the untouched remaining frames.
    
    OUTPUT CONTAINER: MKV with FFV1 codec
    - MP4 + libx264 cannot preserve LSBs reliably (codec treats patterns as noise).
    - MKV + FFV1 (FFmpeg lossless codec) with bgr0 pixel format preserves every byte.
    - This is the only container that guarantees 100% LSB recovery (mae=0.0).
    """
    first_frame, fps, frame_count = video.probe_video(cover_path)
    secret_img = _load_secret_image(secret_path)
    secret_bytes, secret_meta = _serialize_secret(secret_img)

    # Perform capacity check against full video
    capacity.check_capacity(
        cover_shape=first_frame.shape,
        b=b,
        secret_size=len(secret_bytes),
        frame_count=frame_count,
    )

    # Calculate exact frames needed via ceil((bytes * 8) / (H * W * C * b))
    h, w, c = first_frame.shape
    bits_needed = len(secret_bytes) * 8
    capacity_per_frame = h * w * c * b
    frames_needed = max(1, math.ceil(bits_needed / capacity_per_frame))
    
    # Read only the necessary subset of frames
    cover_stack, _ = video.extract_partial_frame_stack(cover_path, frames_needed)

    seed = spread.key_to_seed(key)
    encrypted = crypto.xor_bytes(secret_bytes, seed)

    # In-place embed avoids creating a second tensor
    stego_stack = lsb.embed(cover_stack, encrypted, b, seed, inplace=True)

    def _stream_video() -> collections.abc.Iterator[np.ndarray]:
        # Yield embedded frames
        for frame in stego_stack:
            yield frame
        
        # Stream the remaining frames directly without building a massive list
        idx = 0
        for frame in iio.imiter(cover_path, plugin="pyav"):
            if idx >= frames_needed:
                yield np.ascontiguousarray(frame)
            idx += 1

    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
        stego_path = tmp.name
    
    video.reconstruct_video(_stream_video(), stego_path, fps)

    meta = {
        "mode": "image_in_video",
        "secret_len": len(secret_bytes),
        "secret_shape": list(secret_meta["shape"]),
        "secret_dtype": str(secret_meta["dtype"]),
        "b": b,
        "fps": None,
        "frame_count": frames_needed,  # Decoders must strictly rely on this
    }
    return stego_path, meta


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Inverse pipeline. Returns path to recovered PNG."""
    for field in ("secret_len", "secret_shape", "secret_dtype", "frame_count"):
        if field not in meta:
            raise ValueError(f"missing required meta field: {field}")

    secret_len = int(meta["secret_len"])
    secret_shape = list(meta["secret_shape"])
    secret_dtype = str(meta["secret_dtype"])

    # Number of frames modified during embedding (crucial for accurate PRNG matching).
    # Fallback to loading all frames if absent or None for backward compatibility.
    frames_needed = meta.get("frame_count")
    if frames_needed is not None:
        stego_stack, _ = video.extract_partial_frame_stack(stego_path, int(frames_needed))
    else:
        stego_stack, _ = video.extract_frame_stack(stego_path)

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
