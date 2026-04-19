"""@st.cache_data wrappers and file hash utility."""

from __future__ import annotations

import hashlib
import os
import tempfile

import numpy as np
import streamlit as st

from preprocessing.video import extract_frames


def file_hash(file_bytes: bytes) -> str:
    """Return sha1 hex digest. Used as cache key for uploaded files."""
    return hashlib.sha1(file_bytes).hexdigest()


@st.cache_data(show_spinner=False)
def cached_load_image(file_bytes: bytes) -> np.ndarray:
    """Cache-wrapped preprocessing.image.load_image."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_extract_frames(file_bytes: bytes) -> tuple[list[np.ndarray], float]:
    """Cache-wrapped preprocessing.video.extract_frames.

    Writes file_bytes to temp file (required by pyav plugin which reads from path,
    not buffer), calls extract_frames, cleans up temp file.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return extract_frames(tmp_path)
    finally:
        os.unlink(tmp_path)


@st.cache_data(show_spinner=False)
def cached_embed(mode: str, cover_bytes: bytes, secret_bytes: bytes, key: str, b: int) -> tuple[str, dict]:
    """Cache-wrapped embed call dispatched by mode string."""
    raise NotImplementedError


@st.cache_data(show_spinner=False)
def cached_decode(mode: str, stego_bytes: bytes, key: str, b: int, meta: dict) -> str:
    """Cache-wrapped decode call dispatched by mode string."""
    raise NotImplementedError
