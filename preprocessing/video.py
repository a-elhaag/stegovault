"""Video I/O via imageio v3 pyav plugin. No subprocess calls.

WARNING: H.264 video codecs are incompatible with LSB steganography.
The codec treats embedded secrets (which appear as pseudorandom bits) as noise
and aggressively corrupts them. For LSB embedding in video, use:
- Uncompressed formats (AVI with rawvideo)
- Image sequences (PNG per frame)
- Custom binary containers
Or store the secret alongside the cover without embedding it in the pixels.
"""

from __future__ import annotations

import collections.abc
import logging
import os

import imageio.v3 as iio
import numpy as np

_LOG = logging.getLogger(__name__)
_MEMORY_WARN_BYTES = 512 * 1024 * 1024


def probe_video(video_path: str) -> tuple[np.ndarray, float, int]:
    """Return (first_frame, fps, frame_count) with O(1) frame memory.

    Unlike extract_frames(), this does not keep every frame in memory. It is
    intended for UI preview and capacity estimation on large uploads.
    """
    meta = iio.immeta(video_path, plugin="pyav")
    fps = float(meta["fps"])

    first_frame: np.ndarray | None = None
    frame_count = 0

    for frame in iio.imiter(video_path, plugin="pyav"):
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        if first_frame is None:
            first_frame = np.ascontiguousarray(frame)
        frame_count += 1

    if first_frame is None or frame_count <= 0:
        raise ValueError(f"no frames decoded from {video_path}")

    return first_frame, fps, frame_count


def extract_frames(video_path: str) -> tuple[list[np.ndarray], float]:
    """Return (frames, fps). Each frame is (H, W, 3) uint8.

    Uses imageio.v3 with plugin='pyav'. fps from iio.immeta.
    Streams frames to minimize peak memory (1× video size, not 2×).
    Warns if uncompressed size exceeds ~512 MB (Streamlit Cloud limit).
    """
    meta = iio.immeta(video_path, plugin="pyav")
    fps = float(meta["fps"])

    frames: list[np.ndarray] = []
    running_bytes = 0
    warned = False

    for frame in iio.imiter(video_path, plugin="pyav"):
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        frames.append(np.ascontiguousarray(frame))
        running_bytes += frame.nbytes
        if not warned and running_bytes > _MEMORY_WARN_BYTES:
            _LOG.warning(
                "video uncompressed size >%d MB; may OOM on Streamlit Cloud",
                _MEMORY_WARN_BYTES // (1024 * 1024),
            )
            warned = True

    if not frames:
        raise ValueError(f"no frames decoded from {video_path}")

    return frames, fps


def extract_frame_stack(video_path: str) -> tuple[np.ndarray, float]:
    """Return (frame_stack, fps) where stack shape is (F, H, W, 3) uint8.

    This avoids building a Python list and then stacking it, which doubles memory
    transiently. Uses a probe pass to get exact frame_count and shape, then fills
    a pre-allocated array in a second decode pass.
    """
    first_frame, fps, frame_count = probe_video(video_path)

    h, w, c = first_frame.shape
    frame_stack = np.empty((frame_count, h, w, c), dtype=np.uint8)

    idx = 0
    for frame in iio.imiter(video_path, plugin="pyav"):
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        if frame.shape != (h, w, c):
            raise ValueError(
                f"inconsistent frame shape: {frame.shape} (expected {(h, w, c)})"
            )
        if idx >= frame_count:
            raise ValueError("decoded more frames than reported during probe")
        frame_stack[idx] = frame
        idx += 1

    if idx != frame_count:
        raise ValueError(
            f"decoded frame count mismatch: got {idx}, expected {frame_count}"
        )

    if frame_stack.nbytes > _MEMORY_WARN_BYTES:
        _LOG.warning(
            "video uncompressed size >%d MB; may OOM on Streamlit Cloud",
            _MEMORY_WARN_BYTES // (1024 * 1024),
        )

    return frame_stack, fps

def reconstruct_video(
    frames: collections.abc.Iterable[np.ndarray] | np.ndarray | list[np.ndarray],
    output_path: str,
    fps: float,
) -> None:
    """Write video via codec selected by file extension.

    CONTAINER & CODEC SELECTION:
    - .mkv extension: FFV1 lossless codec + bgr0 pixel format
      Guarantees byte-exact preservation (100% LSB recovery, mae=0.0).
      Used for steganography where LSB corruption is unacceptable.
      
    - .mp4 (or other): libx264 lossless attempt with yuv444p
      Theoretically lossless but not guaranteed for LSB-embedded content.
      FFmpeg's libx264 at crf 0 may still corrupt pseudorandom LSBs.
      NOT RECOMMENDED for steganography without extensive testing.
    
    REASON: LSB payloads look like random noise to video codecs.
    Lossy codecs aggressively remove "noise" (our secret). Even lossless
    codecs may apply transforms that corrupt LSBs. FFV1 is specifically
    designed for frame-accurate preservation.

    Args:
        frames: Iterable or array of (H, W, 3) uint8 frames.
        output_path: destination file path (extension drives codec selection).
        fps: frames per second.

    Raises:
        ValueError: if frames list empty or frame has wrong shape/dtype.
    """
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".mkv":
        codec = "ffv1"
        out_pixel_format = "bgr0"
    else:
        # MP4 or other: use libx264 lossless settings
        codec = "libx264"
        out_pixel_format = "yuv444p"

    frame_iter = iter(frames)
    try:
        first_frame = next(frame_iter)
    except StopIteration:
        raise ValueError("no frames to write")

    def _validate_frame(frame: np.ndarray) -> np.ndarray:
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        return np.ascontiguousarray(frame)

    with iio.imopen(
        output_path,
        "w",
        plugin="pyav",
    ) as writer:
        batch: list[np.ndarray] = [_validate_frame(first_frame)]
        batch_size = 16

        def _flush(current_batch: list[np.ndarray], use_codec: bool) -> None:
            if not current_batch:
                return
            writer.write(
                np.stack(current_batch, axis=0),
                codec=codec if use_codec else None,
                fps=int(fps),
                out_pixel_format=out_pixel_format,
            )

        for frame in frame_iter:
            batch.append(_validate_frame(frame))
            if len(batch) >= batch_size:
                _flush(batch, use_codec=True)
                batch = []

        _flush(batch, use_codec=True)

def extract_partial_frame_stack(video_path: str, num_frames: int) -> tuple[np.ndarray, float]:
    """Return (frame_stack, fps) of exactly num_frames from the start.

    Only decodes the required frames, returning an early stack.
    Shape is (num_frames, H, W, 3) uint8.
    """
    first_frame, fps, frame_count = probe_video(video_path)

    if num_frames > frame_count:
        num_frames = frame_count
    
    if num_frames <= 0:
        raise ValueError("num_frames must be > 0")

    h, w, c = first_frame.shape
    frame_stack = np.empty((num_frames, h, w, c), dtype=np.uint8)

    idx = 0
    for frame in iio.imiter(video_path, plugin="pyav"):
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"unexpected frame shape/dtype: {frame.shape}/{frame.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        if frame.shape != (h, w, c):
            raise ValueError(
                f"inconsistent frame shape: {frame.shape} (expected {(h, w, c)})"
            )
        
        frame_stack[idx] = frame
        idx += 1
        if idx >= num_frames:
            break

    return frame_stack, fps
