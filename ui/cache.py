"""@st.cache_data wrappers and file hash utility."""

from __future__ import annotations

import hashlib
import os
import tempfile

import cv2
import numpy as np
import streamlit as st

from modes import image_in_image, image_in_video, video_in_video
from preprocessing.image import load_image
from preprocessing.video import extract_frames, probe_video


def _mode_temp_suffixes(mode: str) -> tuple[str, str, str]:
    """Return (cover_suffix, secret_suffix, stego_suffix) for a mode."""
    suffixes = {
        "image_in_image": (".png", ".png", ".png"),
        "image_in_video": (".mp4", ".png", ".mkv"),
        "video_in_video": (".mp4", ".mp4", ".mp4"),
    }
    if mode not in suffixes:
        raise ValueError(f"unsupported mode: {mode}")
    return suffixes[mode]


def _embed_dispatch(
    mode: str, cover_path: str, secret_path: str, key: str, b: int
) -> tuple[str, dict]:
    """Dispatch embed call to the requested mode implementation."""
    dispatch = {
        "image_in_image": image_in_image.embed,
        "image_in_video": image_in_video.embed,
        "video_in_video": video_in_video.embed,
    }
    if mode not in dispatch:
        raise ValueError(f"unsupported mode: {mode}")
    return dispatch[mode](cover_path, secret_path, key, b)


def _decode_dispatch(mode: str, stego_path: str, key: str, b: int, meta: dict) -> str:
    """Dispatch decode call to the requested mode implementation."""
    dispatch = {
        "image_in_image": image_in_image.decode,
        "image_in_video": image_in_video.decode,
        "video_in_video": video_in_video.decode,
    }
    if mode not in dispatch:
        raise ValueError(f"unsupported mode: {mode}")
    return dispatch[mode](stego_path, key, b, meta)


def file_hash(file_bytes: bytes) -> str:
    """Return sha1 hex digest. Used as cache key for uploaded files."""
    return hashlib.sha1(file_bytes).hexdigest()


@st.cache_data(show_spinner=False)
def cached_load_image(file_bytes: bytes) -> np.ndarray:
    """Cache-wrapped preprocessing.image.load_image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        try:
            img = load_image(tmp_path)
        except NotImplementedError:
            img = cv2.imread(tmp_path, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("failed to decode image bytes")

        if img.dtype != np.uint8 or img.ndim != 3 or img.shape[2] != 3:
            raise ValueError(
                f"unexpected image shape/dtype: {img.shape}/{img.dtype} "
                f"(expected (H, W, 3) uint8)"
            )
        return np.ascontiguousarray(img)
    finally:
        os.unlink(tmp_path)


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
def cached_probe_video(file_bytes: bytes) -> tuple[np.ndarray, float, int]:
    """Cache-wrapped preprocessing.video.probe_video.

    Returns first frame, fps, and frame count without retaining all decoded
    frames in memory.
    """
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return probe_video(tmp_path)
    finally:
        os.unlink(tmp_path)


@st.cache_data(show_spinner=False)
def cached_embed(
    mode: str, cover_bytes: bytes, secret_bytes: bytes, key: str, b: int
) -> tuple[str, dict]:
    """Cache-wrapped embed call dispatched by mode string."""
    cover_suffix, secret_suffix, _ = _mode_temp_suffixes(mode)

    with tempfile.NamedTemporaryFile(suffix=cover_suffix, delete=False) as cover_tmp:
        cover_tmp.write(cover_bytes)
        cover_path = cover_tmp.name
    with tempfile.NamedTemporaryFile(suffix=secret_suffix, delete=False) as secret_tmp:
        secret_tmp.write(secret_bytes)
        secret_path = secret_tmp.name

    try:
        return _embed_dispatch(mode, cover_path, secret_path, key, b)
    finally:
        os.unlink(cover_path)
        os.unlink(secret_path)


@st.cache_data(show_spinner=False)
def cached_decode(mode: str, stego_bytes: bytes, key: str, b: int, meta: dict) -> str:
    """Cache-wrapped decode call dispatched by mode string."""
    _, _, stego_suffix = _mode_temp_suffixes(mode)
    with tempfile.NamedTemporaryFile(suffix=stego_suffix, delete=False) as stego_tmp:
        stego_tmp.write(stego_bytes)
        stego_path = stego_tmp.name
    try:
        return _decode_dispatch(mode, stego_path, key, b, meta)
    finally:
        os.unlink(stego_path)
