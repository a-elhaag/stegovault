"""Tests for modes.image_in_video: embed, decode."""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from modes.image_in_video import embed, decode


# ================= Helpers =================
def create_test_video(path: str, frame_shape=(64, 64, 3), n_frames=10):
    """Create a simple test video."""
    fourcc = cv2.VideoWriter_fourcc(*'FFV1')  # lossless
    out = cv2.VideoWriter(path, fourcc, 25.0, (frame_shape[1], frame_shape[0]))

    for _ in range(n_frames):
        frame = np.random.randint(0, 256, frame_shape, dtype=np.uint8)
        out.write(frame)

    out.release()


def create_test_image(path: str, shape: tuple):
    img = np.random.randint(0, 256, shape, dtype=np.uint8)
    cv2.imwrite(path, img)


# ================= Tests =================

def test_embed_creates_stego_video():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        create_test_video(video_path)
        create_test_image(image_path, (32, 32, 3))

        stego_path, meta = embed(video_path, image_path, "testkey", b=2)

        assert Path(stego_path).exists()
        assert Path(stego_path).stat().st_size > 0


def test_embed_returns_meta_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        create_test_video(video_path)
        create_test_image(image_path, (20, 20, 3))

        _, meta = embed(video_path, image_path, "testkey", b=2)

        assert meta["mode"] == "image_in_video"
        assert isinstance(meta["secret_len"], int)
        assert meta["secret_len"] > 0
        assert isinstance(meta["secret_shape"], list)
        assert meta["secret_shape"] == [20, 20, 3]
        assert meta["secret_dtype"] == "uint8"
        assert meta["b"] == 2
        assert "fps" in meta
        assert "frame_count" in meta


def test_decode_recovers_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        # fixed image
        original = np.array(
            [[[10, 20, 30], [40, 50, 60]],
             [[70, 80, 90], [100, 110, 120]]],
            dtype=np.uint8,
        )

        create_test_video(video_path)
        cv2.imwrite(image_path, original)

        key = "securekey"
        b = 2

        stego_path, meta = embed(video_path, image_path, key, b)
        recovered_path = decode(stego_path, key, b, meta)

        recovered = cv2.imread(recovered_path)

        assert recovered is not None
        assert recovered.shape == original.shape
        assert recovered.dtype == original.dtype
        assert np.array_equal(recovered, original)


def test_wrong_key_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        create_test_video(video_path)
        create_test_image(image_path, (16, 16, 3))

        stego_path, meta = embed(video_path, image_path, "correct", b=2)

        with pytest.raises(ValueError):
            decode(stego_path, "wrong", b=2, meta=meta)


def test_embed_respects_b_values():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        create_test_video(video_path)
        create_test_image(image_path, (16, 16, 3))

        for b in [1, 2, 3, 4]:
            stego_path, meta = embed(video_path, image_path, "key", b)
            assert meta["b"] == b

            recovered_path = decode(stego_path, "key", b, meta)
            assert Path(recovered_path).exists()


def test_embed_rejects_invalid_b():
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = str(Path(tmpdir) / "input.mkv")
        image_path = str(Path(tmpdir) / "secret.png")

        create_test_video(video_path)
        create_test_image(image_path, (16, 16, 3))

        for invalid_b in [0, 5, -1]:
            with pytest.raises(ValueError):
                embed(video_path, image_path, "key", invalid_b)
