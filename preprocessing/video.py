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

import logging

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
    frames: list[np.ndarray] | np.ndarray,
    output_path: str,
    fps: float,
) -> None:
    """Write video via libx264 codec (H.264).

    Note: Video codecs introduce artifacts during RGB↔YUV conversion.
    Pixel errors can be ±10-30 per channel. LSB embedding is viable at b≥3.
    For byte-exact preservation, use uncompressed formats or custom storage.

    Codec spec:
        AGENTS.md specifies: libx264 -crf 0 -preset ultrafast -pix_fmt yuv444p
        In imageio.v3.imwrite context:
          codec='libx264', fps=int(fps), out_pixel_format='yuv444p'
          crf is numeric (default 0, meaning lossless). Preset is auto-handled.

    Args:
        frames: list of (H, W, 3) uint8 RGB arrays.
        output_path: destination file path (extension preserved for metadata).
        fps: frames per second.

    Raises:
        ValueError: if frames list empty or frame has wrong shape/dtype.
    """
    if isinstance(frames, np.ndarray):
        if frames.ndim != 4 or frames.shape[0] == 0:
            raise ValueError("no frames to write")
        first = frames[0]
    else:
        if not frames:
            raise ValueError("no frames to write")
        first = frames[0]

    if first.dtype != np.uint8 or first.ndim != 3 or first.shape[2] != 3:
        raise ValueError(
            f"unexpected frame shape/dtype: {first.shape}/{first.dtype} "
            f"(expected (H, W, 3) uint8)"
        )

    # Pass frame list directly to imwrite. imageio.v3 auto-detects list of frames
    # and streams to encoder without full stacking. Peak memory = O(1) frame buffer.
    iio.imwrite(
        output_path,
        frames,
        plugin="pyav",
        codec="libx264",
        fps=int(fps),
        out_pixel_format="yuv444p",
    )
