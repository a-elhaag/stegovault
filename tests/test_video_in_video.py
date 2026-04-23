"""Tests for modes.video_in_video: embed, decode."""

from __future__ import annotations

import os
import tempfile

import numpy as np

from modes.video_in_video import decode, embed
from preprocessing.video import extract_frame_stack, reconstruct_video


def _make_video_pair() -> tuple[str, str, np.ndarray, np.ndarray, float, float]:
    """Create temporary cover and secret MKV videos for integration tests."""
    rng = np.random.default_rng(11)

    cover_frames = [rng.integers(0, 256, (32, 32, 3), dtype=np.uint8) for _ in range(12)]
    secret_frames = [rng.integers(0, 256, (32, 32, 3), dtype=np.uint8) for _ in range(2)]

    cover_fps = 24.0
    secret_fps = 15.0

    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as ctmp:
        cover_path = ctmp.name
    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as stmp:
        secret_path = stmp.name

    reconstruct_video(cover_frames, cover_path, cover_fps)
    reconstruct_video(secret_frames, secret_path, secret_fps)

    return (
        cover_path,
        secret_path,
        np.stack(cover_frames, axis=0),
        np.stack(secret_frames, axis=0),
        cover_fps,
        secret_fps,
    )


def test_embed_creates_stego_video() -> None:
    cover_path, secret_path, *_ = _make_video_pair()
    try:
        stego_path, _ = embed(cover_path, secret_path, key="test-key", b=3)
        try:
            assert os.path.exists(stego_path)
            assert os.path.getsize(stego_path) > 0
            assert stego_path.endswith(".mkv")
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)
    finally:
        if os.path.exists(cover_path):
            os.unlink(cover_path)
        if os.path.exists(secret_path):
            os.unlink(secret_path)


def test_embed_returns_meta_keys() -> None:
    cover_path, secret_path, _, secret_frames, _, secret_fps = _make_video_pair()
    try:
        stego_path, meta = embed(cover_path, secret_path, key="meta-key", b=2)
        try:
            assert meta["mode"] == "video_in_video"
            assert isinstance(meta["secret_len"], int)
            assert isinstance(meta["secret_shape"], list)
            assert meta["secret_shape"] == [32, 32, 3]
            assert meta["secret_dtype"] == "uint8"
            assert meta["b"] == 2
            assert meta["fps"] == secret_fps
            assert meta["frame_count"] == secret_frames.shape[0]
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)
    finally:
        if os.path.exists(cover_path):
            os.unlink(cover_path)
        if os.path.exists(secret_path):
            os.unlink(secret_path)


def test_decode_recovers_video() -> None:
    cover_path, secret_path, _, secret_frames, _, secret_fps = _make_video_pair()
    try:
        stego_path, meta = embed(cover_path, secret_path, key="decode-key", b=4)
        try:
            recovered_path = decode(stego_path, key="decode-key", b=4, meta=meta)
            try:
                recovered_frames, recovered_fps = extract_frame_stack(recovered_path)
                assert recovered_frames.shape == secret_frames.shape
                assert np.array_equal(recovered_frames, secret_frames)
                assert abs(recovered_fps - secret_fps) < 1.0
            finally:
                if os.path.exists(recovered_path):
                    os.unlink(recovered_path)
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)
    finally:
        if os.path.exists(cover_path):
            os.unlink(cover_path)
        if os.path.exists(secret_path):
            os.unlink(secret_path)


def test_grayscale_fallback_roundtrip() -> None:
    """If the color secret is too large, the mode should fall back to grayscale."""
    rng = np.random.default_rng(23)
    cover_frames = [rng.integers(0, 256, (32, 32, 3), dtype=np.uint8) for _ in range(12)]
    secret_frames = [rng.integers(0, 256, (32, 32, 3), dtype=np.uint8) for _ in range(4)]
    secret_fps = 15.0

    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as ctmp:
        cover_path = ctmp.name
    with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as stmp:
        secret_path = stmp.name

    reconstruct_video(cover_frames, cover_path, 24.0)
    reconstruct_video(secret_frames, secret_path, secret_fps)

    try:
        stego_path, meta = embed(cover_path, secret_path, key="gray-key", b=2)
        try:
            assert meta["secret_shape"] == [32, 32, 1]
            recovered_path = decode(stego_path, key="gray-key", b=2, meta=meta)
            try:
                recovered_frames, recovered_fps = extract_frame_stack(recovered_path)
                secret_stack = np.stack(secret_frames, axis=0)
                gray_frames = np.rint(
                    0.114 * secret_stack[..., 0].astype(np.float32)
                    + 0.587 * secret_stack[..., 1].astype(np.float32)
                    + 0.299 * secret_stack[..., 2].astype(np.float32)
                ).astype(np.uint8)
                gray_frames = np.repeat(gray_frames[..., np.newaxis], 3, axis=-1)
                assert recovered_frames.shape == gray_frames.shape
                assert np.array_equal(recovered_frames, gray_frames)
                assert abs(recovered_fps - secret_fps) < 1.0
            finally:
                if os.path.exists(recovered_path):
                    os.unlink(recovered_path)
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)
    finally:
        if os.path.exists(cover_path):
            os.unlink(cover_path)
        if os.path.exists(secret_path):
            os.unlink(secret_path)
