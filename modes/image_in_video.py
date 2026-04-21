from __future__ import annotations

from pathlib import Path
import numpy as np

from engine import capacity, crypto, lsb, spread
from preprocessing import image as preprocess_image
from preprocessing import video as preprocess_video


# ================= EMBED =================
def embed(video_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """
    Full image-in-video pipeline.

    Returns:
        (stego_video_path, meta)
    """

    if b not in range(1, 5):
        raise ValueError(f"b must be in [1, 4], got {b}")

    # 1. extract frames
    frames, fps = preprocess_video.extract_frames(video_path)

    if len(frames) == 0:
        raise ValueError("Video has no frames")

    # 2. load + serialize secret image
    secret = preprocess_image.load_image(secret_path)
    secret_bytes = preprocess_image.serialize_image(secret)

    # 3. capacity check (total pixels in all frames)
    total_pixels = sum(frame.size for frame in frames)
    capacity.check_capacity((total_pixels,), b, len(secret_bytes))

    # 4. key → seed
    seed = spread.key_to_seed(key)

    # 5. encrypt
    encrypted = crypto.xor_bytes(secret_bytes, seed)

    # 6. flatten all frames into one big array
    flat = np.concatenate([f.flatten() for f in frames])

    # 7. embed using LSB engine
    stego_flat = lsb.embed(flat, encrypted, b, seed)

    # 8. reshape back to frames
    idx = 0
    new_frames = []
    for f in frames:
        size = f.size
        new_f = stego_flat[idx:idx+size].reshape(f.shape)
        new_frames.append(new_f)
        idx += size

    # 9. reconstruct video
    output_path = str(Path(video_path).parent / "stego_video.mkv")
    preprocess_video.reconstruct_video(new_frames, output_path, fps)

    # 10. metadata
    meta = {
        "mode": "image_in_video",
        "secret_len": len(secret_bytes),
        "secret_shape": list(secret.shape),
        "secret_dtype": "uint8",
        "b": b,
        "fps": fps,
        "frame_count": len(frames),
    }

    return output_path, meta


# ================= DECODE =================
def decode(stego_video_path: str, key: str, b: int, meta: dict) -> str:
    """
    Recover hidden image from video.
    """

    if b not in range(1, 5):
        raise ValueError(f"b must be in [1, 4], got {b}")

    # 1. extract frames
    frames, _ = preprocess_video.extract_frames(stego_video_path)

    if len(frames) == 0:
        raise ValueError("Video has no frames")

    # 2. flatten frames
    flat = np.concatenate([f.flatten() for f in frames])

    # 3. regenerate seed
    seed = spread.key_to_seed(key)

    # 4. decode encrypted bytes
    secret_len = meta["secret_len"]
    encrypted = lsb.decode(flat, b, seed, secret_len)

    # 5. decrypt
    secret_bytes = crypto.xor_bytes(encrypted, seed)

    # 6. deserialize image
    secret = preprocess_image.deserialize_image(secret_bytes)

    # 7. save result
    output_path = str(Path(stego_video_path).parent / "recovered_secret.png")
    preprocess_image.save_image(secret, output_path)

    return output_path
