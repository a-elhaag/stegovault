"""Mode: video secret hidden inside video cover. Owner: Youstina."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from engine import capacity, crypto, lsb, spread
from preprocessing import video as preprocess_video


def _validate_b(b: int) -> None:
	if b not in range(1, 5):
		raise ValueError(f"b must be in [1, 4], got {b}")


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
	"""Embed secret video inside cover video and return (stego_path, meta)."""
	_validate_b(b)

	cover_frames, cover_fps = preprocess_video.extract_frames(cover_path)
	secret_frames, secret_fps = preprocess_video.extract_frames(secret_path)

	cover_arr = np.stack(cover_frames, axis=0)
	secret_arr = np.stack(secret_frames, axis=0)

	secret_bytes = secret_arr.tobytes()
	capacity.check_capacity(
		cover_shape=cover_arr.shape[1:],
		b=b,
		secret_size=len(secret_bytes),
		frame_count=cover_arr.shape[0],
	)

	seed = spread.key_to_seed(key)
	encrypted = crypto.xor_bytes(secret_bytes, seed)
	stego_arr = lsb.embed(cover_arr, encrypted, b, seed)

	output_path = str(Path(cover_path).parent / "stego_output.mp4")
	preprocess_video.reconstruct_video(
		[np.ascontiguousarray(frame) for frame in stego_arr],
		output_path,
		cover_fps,
	)

	meta = {
		"mode": "video_in_video",
		"secret_len": len(secret_bytes),
		"secret_shape": list(secret_arr.shape[1:]),
		"secret_dtype": "uint8",
		"b": b,
		"fps": float(secret_fps),
		"frame_count": int(secret_arr.shape[0]),
	}
	return output_path, meta


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
	"""Decode secret video from stego video and return recovered path."""
	_validate_b(b)

	stego_frames, _ = preprocess_video.extract_frames(stego_path)
	stego_arr = np.stack(stego_frames, axis=0)

	seed = spread.key_to_seed(key)
	encrypted = lsb.decode(stego_arr, b, seed, int(meta["secret_len"]))
	secret_bytes = crypto.xor_bytes(encrypted, seed)

	frame_count = int(meta["frame_count"])
	h, w, c = [int(v) for v in meta["secret_shape"]]
	expected_bytes = frame_count * h * w * c
	if len(secret_bytes) < expected_bytes:
		raise ValueError(
			"decoded secret length is smaller than expected frame payload; "
			"data may be corrupted or key/meta is incorrect"
		)

	secret_arr = np.frombuffer(secret_bytes, dtype=np.uint8, count=expected_bytes)
	secret_arr = secret_arr.reshape((frame_count, h, w, c))

	output_path = str(Path(stego_path).parent / "recovered_secret.mp4")
	preprocess_video.reconstruct_video(
		[np.ascontiguousarray(frame) for frame in secret_arr],
		output_path,
		float(meta["fps"]),
	)
	return output_path
