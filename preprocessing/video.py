"""Lossless video I/O via imageio v3 pyav plugin. No subprocess calls."""

from __future__ import annotations

import numpy as np


def extract_frames(video_path: str) -> tuple[list[np.ndarray], float]:
    """Return (frames, fps). Each frame is (H, W, 3) uint8.

    Uses imageio.v3 with plugin='pyav'. fps from iio.immeta.
    """
    raise NotImplementedError


def reconstruct_video(
    frames: list[np.ndarray],
    output_path: str,
    fps: float,
) -> None:
    """Write lossless MP4 via imageio.v3 / pyav.

    Codec libx264, -crf 0 -preset ultrafast -pix_fmt yuv444p.
    Preserves LSBs across codec round-trip.
    """
    raise NotImplementedError
