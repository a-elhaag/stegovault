"""@st.cache_data wrappers and file hash utility."""

from __future__ import annotations

import numpy as np


def file_hash(file_bytes: bytes) -> str:
    """Return sha1 hex digest. Used as cache key for uploaded files."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_load_image(file_bytes: bytes) -> np.ndarray:
    """Cache-wrapped preprocessing.image.load_image."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_extract_frames(file_bytes: bytes) -> tuple[list[np.ndarray], float]:
    """Cache-wrapped preprocessing.video.extract_frames."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_embed(mode: str, cover_bytes: bytes, secret_bytes: bytes, key: str, b: int) -> tuple[str, dict]:
    """Cache-wrapped embed call dispatched by mode string."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_decode(mode: str, stego_bytes: bytes, key: str, b: int, meta: dict) -> str:
    """Cache-wrapped decode call dispatched by mode string."""
    raise NotImplementedError
