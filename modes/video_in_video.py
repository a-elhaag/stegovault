"""Mode: video secret hidden inside video cover. Owner: Youstina."""

from __future__ import annotations

import collections.abc
import tempfile

import cv2
import imageio.v3 as iio
import numpy as np

from engine import capacity, crypto, lsb, spread
from preprocessing import video

_FULL_STACK_LIMIT_BYTES = 50 * 1024 * 1024


def _validate_frame(frame: np.ndarray) -> np.ndarray:
  """Validate a decoded frame and normalize it to contiguous uint8 BGR."""
  if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
    raise ValueError(
      f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
      f"(expected (H, W, 3) uint8)"
    )
  return np.ascontiguousarray(frame)


def _frame_capacity_bytes(frame_shape: tuple[int, int, int], b: int) -> int:
  """Return the number of payload bytes one frame can carry at bit depth b."""
  h, w, c = frame_shape
  return (h * w * c * b) // 8


def _total_payload_bytes(frame_count: int, frame_shape: tuple[int, int, int]) -> int:
  """Return the raw byte size of a serialized frame stack."""
  h, w, c = frame_shape
  return int(frame_count) * int(h) * int(w) * int(c)


def _resize_secret_stack(secret_stack: np.ndarray, target_shape: tuple[int, int, int], grayscale: bool) -> np.ndarray:
  """Resize a full secret stack for the exact small-video path."""
  target_h, target_w, target_c = target_shape
  if target_c != 3:
    raise ValueError(f"expected RGB/BGR cover frames with 3 channels, got {target_c}")

  resized_frames: list[np.ndarray] = []
  for frame in secret_stack:
    frame = _validate_frame(frame)
    if frame.shape[:2] != (target_h, target_w):
      frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
    if grayscale:
      frame = np.rint(
        0.114 * frame[..., 0].astype(np.float32)
        + 0.587 * frame[..., 1].astype(np.float32)
        + 0.299 * frame[..., 2].astype(np.float32)
      ).astype(np.uint8)[..., np.newaxis]
    resized_frames.append(np.ascontiguousarray(frame))

  return np.stack(resized_frames, axis=0)


def _stream_resized_secret_frames(
  secret_path: str,
  target_shape: tuple[int, int, int],
  grayscale: bool,
) -> collections.abc.Iterator[np.ndarray]:
  """Yield resized secret frames one at a time."""
  target_h, target_w, target_c = target_shape
  if target_c != 3:
    raise ValueError(f"expected RGB/BGR cover frames with 3 channels, got {target_c}")

  for frame in iio.imiter(secret_path, plugin="pyav"):
    frame = _validate_frame(frame)
    if frame.shape[:2] != (target_h, target_w):
      frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
    if grayscale:
      gray = np.rint(
        0.114 * frame[..., 0].astype(np.float32)
        + 0.587 * frame[..., 1].astype(np.float32)
        + 0.299 * frame[..., 2].astype(np.float32)
      ).astype(np.uint8)
      yield gray[..., np.newaxis]
    else:
      yield frame


def embed_video(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
  """Hide a secret video inside a cover video without materializing giant arrays."""
  cover_first, cover_fps, cover_count = video.probe_video(cover_path)
  _, secret_fps, secret_count = video.probe_video(secret_path)

  cover_shape = cover_first.shape
  if cover_shape[2] != 3:
    raise ValueError(f"expected cover frames with 3 channels, got {cover_shape[2]}")

  color_secret_len = _total_payload_bytes(secret_count, cover_shape)
  gray_secret_len = _total_payload_bytes(secret_count, (cover_shape[0], cover_shape[1], 1))
  capacity_bytes = _frame_capacity_bytes(cover_shape, b) * cover_count

  grayscale = False
  secret_shape = [cover_shape[0], cover_shape[1], 3]
  secret_len = color_secret_len

  if color_secret_len <= capacity_bytes:
    grayscale = False
  elif gray_secret_len <= capacity_bytes:
    grayscale = True
    secret_shape = [cover_shape[0], cover_shape[1], 1]
    secret_len = gray_secret_len
  else:
    capacity.check_capacity(cover_shape, b, color_secret_len, frame_count=cover_count)

  capacity.check_capacity(cover_shape, b, secret_len, frame_count=cover_count)

  if (cover_count * cover_shape[0] * cover_shape[1] * cover_shape[2] <= _FULL_STACK_LIMIT_BYTES
      and secret_len <= _FULL_STACK_LIMIT_BYTES):
    cover_stack, cover_fps = video.extract_frame_stack(cover_path)
    secret_stack, secret_fps = video.extract_frame_stack(secret_path)
    resized_secret = _resize_secret_stack(secret_stack, cover_stack[0].shape, grayscale)
    secret_bytes = np.ascontiguousarray(resized_secret).tobytes()

    seed = spread.key_to_seed(key)
    encrypted = crypto.xor_bytes(secret_bytes, seed)
    stego_stack = lsb.embed(cover_stack, encrypted, b, seed, inplace=False)

    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
      stego_path = tmp.name

    video.reconstruct_video(stego_stack, stego_path, cover_fps)

    meta = {
      "mode": "video_in_video",
      "secret_len": len(secret_bytes),
      "secret_shape": list(resized_secret.shape[1:]),
      "secret_dtype": "uint8",
      "b": b,
      "fps": secret_fps,
      "frame_count": int(secret_count),
    }
    return stego_path, meta

  seed = spread.key_to_seed(key)
  frame_capacity = _frame_capacity_bytes(cover_shape, b)
  secret_iter = _stream_resized_secret_frames(secret_path, cover_shape, grayscale)
  secret_buffer = bytearray()
  secret_source_exhausted = False
  emitted_secret_bytes = 0

  def _fill_secret_buffer() -> None:
    nonlocal secret_source_exhausted
    while len(secret_buffer) < frame_capacity and not secret_source_exhausted:
      try:
        secret_buffer.extend(next(secret_iter).tobytes())
      except StopIteration:
        secret_source_exhausted = True
        break

  def _cover_stream() -> collections.abc.Iterator[np.ndarray]:
    nonlocal emitted_secret_bytes
    for frame_index, cover_frame in enumerate(iio.imiter(cover_path, plugin="pyav")):
      cover_frame = _validate_frame(cover_frame)
      if emitted_secret_bytes >= secret_len:
        yield cover_frame
        continue

      _fill_secret_buffer()
      take = min(frame_capacity, len(secret_buffer), secret_len - emitted_secret_bytes)
      if take <= 0:
        yield cover_frame
        continue

      chunk = bytes(secret_buffer[:take])
      del secret_buffer[:take]
      emitted_secret_bytes += take
      yield lsb.embed(cover_frame, chunk, b, seed + frame_index)

  with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
    stego_path = tmp.name

  video.reconstruct_video(_cover_stream(), stego_path, cover_fps)

  meta = {
    "mode": "video_in_video",
    "secret_len": secret_len,
    "secret_shape": secret_shape,
    "secret_dtype": "uint8",
    "b": b,
    "fps": secret_fps,
    "frame_count": int(secret_count),
  }
  return stego_path, meta


def extract_video(stego_path: str, key: str, b: int, meta: dict) -> str:
  """Recover a secret video from a stego video using the provided metadata."""
  for field in ("secret_len", "secret_shape", "secret_dtype", "frame_count"):
    if field not in meta:
      raise ValueError(f"missing required meta field: {field}")

  secret_len = int(meta["secret_len"])
  secret_shape = list(meta["secret_shape"])
  secret_dtype = np.dtype(str(meta["secret_dtype"]))
  frame_count = int(meta["frame_count"])
  if secret_dtype != np.dtype("uint8"):
    raise ValueError(f"unsupported secret dtype: {secret_dtype}")
  if len(secret_shape) != 3:
    raise ValueError(f"secret_shape must describe one frame: {secret_shape}")
  if frame_count <= 0:
    raise ValueError(f"frame_count must be positive, got {frame_count}")

  if secret_len <= _FULL_STACK_LIMIT_BYTES:
    stego_stack, _ = video.extract_frame_stack(stego_path)
    seed = spread.key_to_seed(key)
    encrypted = lsb.decode(stego_stack, b, seed, secret_len)
    secret_bytes = crypto.xor_bytes(encrypted, seed)

    expected_bytes = frame_count * int(np.prod(secret_shape))
    if len(secret_bytes) != expected_bytes:
      raise ValueError(
        f"decoded secret byte length mismatch: got {len(secret_bytes)}, expected {expected_bytes}"
      )

    secret_stack = np.frombuffer(secret_bytes, dtype=np.uint8).reshape((frame_count, *secret_shape))
    if secret_stack.shape[-1] == 1:
      secret_stack = np.repeat(secret_stack, 3, axis=-1)

    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
      out_path = tmp.name

    secret_fps = float(meta["fps"]) if meta.get("fps") is not None else 0.0
    video.reconstruct_video(secret_stack, out_path, secret_fps)
    return out_path

  seed = spread.key_to_seed(key)
  secret_frame_bytes = int(np.prod(secret_shape))
  decoded_buffer = bytearray()
  yielded_frame_count = 0

  def _secret_frame_stream() -> collections.abc.Iterator[np.ndarray]:
    nonlocal yielded_frame_count
    emitted_secret_bytes = 0
    for frame_index, stego_frame in enumerate(iio.imiter(stego_path, plugin="pyav")):
      stego_frame = _validate_frame(stego_frame)
      if emitted_secret_bytes >= secret_len:
        break

      take = min(_frame_capacity_bytes(stego_frame.shape, b), secret_len - emitted_secret_bytes)
      if take <= 0:
        continue

      encrypted_chunk = lsb.decode(stego_frame, b, seed + frame_index, take)
      decoded_buffer.extend(crypto.xor_bytes(encrypted_chunk, seed))
      emitted_secret_bytes += take

      while len(decoded_buffer) >= secret_frame_bytes:
        frame_bytes = bytes(decoded_buffer[:secret_frame_bytes])
        del decoded_buffer[:secret_frame_bytes]
        frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(tuple(secret_shape))
        if frame.shape[2] == 1:
          frame = np.repeat(frame, 3, axis=2)
        yielded_frame_count += 1
        yield frame

  secret_frame_stream = _secret_frame_stream()

  with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
    out_path = tmp.name

  secret_fps = float(meta["fps"]) if meta.get("fps") is not None else 0.0
  video.reconstruct_video(secret_frame_stream, out_path, secret_fps)

  if yielded_frame_count != frame_count:
    raise ValueError(
      f"decoded frame count mismatch: got {yielded_frame_count}, expected {frame_count}"
    )
  if decoded_buffer:
    raise ValueError("decoded secret byte stream ended with leftover bytes")
  return out_path


def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
  """Alias for embed_video to match the cached UI dispatch contract."""
  return embed_video(cover_path, secret_path, key, b)


def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
  """Alias for extract_video to match the cached UI dispatch contract."""
  return extract_video(stego_path, key, b, meta)
