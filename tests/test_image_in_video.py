"""Tests for modes.image_in_video: embed, decode."""

import os
import tempfile

import cv2
import numpy as np

from modes.image_in_video import decode, embed
from preprocessing.video import reconstruct_video


def _make_cover_and_secret() -> tuple[str, str]:
    """Create temporary cover MP4 and secret PNG for tests."""
    rng = np.random.default_rng(7)

    frames = [rng.integers(0, 256, (128, 128, 3), dtype=np.uint8) for _ in range(8)]
    secret = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as ctmp:
        cover_path = ctmp.name
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as stmp:
        secret_path = stmp.name

    reconstruct_video(frames, cover_path, 24.0)
    ok = cv2.imwrite(secret_path, secret)
    if not ok:
        os.unlink(cover_path)
        os.unlink(secret_path)
        raise ValueError("failed to write secret test image")

    return cover_path, secret_path


def test_embed_creates_stego_video() -> None:
    cover_path, secret_path = _make_cover_and_secret()
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
    cover_path, secret_path = _make_cover_and_secret()
    try:
        stego_path, meta = embed(cover_path, secret_path, key="meta-key", b=2)
        try:
            assert meta["mode"] == "image_in_video"
            assert isinstance(meta["secret_len"], int)
            assert isinstance(meta["secret_shape"], list)
            assert meta["secret_dtype"] == "uint8"
            assert meta["b"] == 2
            assert meta["fps"] is None
            assert isinstance(meta["frame_count"], int)
            assert meta["frame_count"] >= 1
        finally:
            if os.path.exists(stego_path):
                os.unlink(stego_path)
    finally:
        if os.path.exists(cover_path):
            os.unlink(cover_path)
        if os.path.exists(secret_path):
            os.unlink(secret_path)


def test_decode_recovers_image() -> None:
    cover_path, secret_path = _make_cover_and_secret()
    try:
        stego_path, meta = embed(cover_path, secret_path, key="decode-key", b=4)
        try:
            recovered_path = decode(stego_path, key="decode-key", b=4, meta=meta)
            try:
                original = cv2.imread(secret_path, cv2.IMREAD_COLOR)
                recovered = cv2.imread(recovered_path, cv2.IMREAD_COLOR)
                assert original is not None
                assert recovered is not None
                assert original.shape == recovered.shape
                assert np.array_equal(original, recovered)
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
