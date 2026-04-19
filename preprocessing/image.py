"""PNG-only image I/O and raw-byte (de)serialization. No Pillow."""

from __future__ import annotations

import numpy as np


def load_image(path: str) -> np.ndarray:
    """Load PNG via cv2.imread. Returns (H, W, 3) uint8 BGR array."""
    raise NotImplementedError


def serialize_image(img: np.ndarray) -> tuple[bytes, dict]:
    """Flatten img to raw bytes.

    Returns (data_bytes, meta) where meta = {'shape': list, 'dtype': str}.
    Caller writes meta to the JSON sidecar so decode can reconstruct shape.
    """
    raise NotImplementedError


def deserialize_image(data: bytes, meta: dict) -> np.ndarray:
    """Reconstruct ndarray from raw bytes + meta dict. Inverse of serialize_image."""
    raise NotImplementedError
