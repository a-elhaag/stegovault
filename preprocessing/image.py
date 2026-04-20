"""PNG-only image I/O and raw-byte (de)serialization. No Pillow."""

from __future__ import annotations

import cv2
import numpy as np

def load_image(path: str) -> np.ndarray:
    """Load an image from a file path using cv2.

    Args:
        path: File path to the image.

    Returns:
        np.ndarray: Image array in BGR format with shape (H, W, C) and dtype uint8.

    Raises:
        ValueError: If the image could not be loaded.
    """
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not load image from {path}")
    return img


def serialize_image(img: np.ndarray) -> bytes:
    """Convert a numpy image array into raw PNG bytes.

    Args:
        img: numpy array representing an image.

    Returns:
        bytes: PNG-encoded image data.

    Raises:
        ValueError: If encoding fails.
    """
    success, encoded = cv2.imencode('.png', img)
    if not success:
        raise ValueError("Failed to encode image as PNG")
    return encoded.tobytes()


def deserialize_image(data: bytes, metadata: dict | None = None) -> np.ndarray:
    """Convert raw PNG bytes back into a numpy image array.

    Args:
        data: PNG-encoded image bytes.
        metadata: Optional dict with keys 'shape' and 'dtype' (unused; for API consistency).
                  PNG format carries shape/dtype in header; this param allows fallback patterns
                  in callers (e.g., image_in_video.py) to pass metadata without error.

    Returns:
        np.ndarray: Image array in BGR format with shape (H, W, C) and dtype uint8.

    Raises:
        ValueError: If decoding fails.
    """
    img_array = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode PNG data")
    return img
