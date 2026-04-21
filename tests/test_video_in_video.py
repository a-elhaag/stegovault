"""Tests for modes.video_in_video: embed, decode."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from modes import video_in_video


def _make_frames(frame_count: int, h: int, w: int) -> list[np.ndarray]:
    rng = np.random.default_rng(123)
    return [rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8) for _ in range(frame_count)]


@pytest.fixture
def fake_video_io(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """In-memory video backend for stable tests without ffmpeg/pyav."""
    store: dict[str, tuple[list[np.ndarray], float]] = {}

    def fake_extract_frames(video_path: str):
        if video_path not in store:
            raise ValueError(f"unknown test video path: {video_path}")
        frames, fps = store[video_path]
        return [np.ascontiguousarray(f.copy()) for f in frames], fps

    def fake_reconstruct_video(frames: list[np.ndarray], output_path: str, fps: float):
        store[output_path] = ([np.ascontiguousarray(f.copy()) for f in frames], float(fps))
        Path(output_path).write_bytes(b"fake-video")

    monkeypatch.setattr(video_in_video.preprocess_video, "extract_frames", fake_extract_frames)
    monkeypatch.setattr(video_in_video.preprocess_video, "reconstruct_video", fake_reconstruct_video)
    return store, tmp_path


def test_embed_creates_stego_video(fake_video_io) -> None:
    store, tmp_path = fake_video_io
    cover_path = str(tmp_path / "cover.mp4")
    secret_path = str(tmp_path / "secret.mp4")

    store[cover_path] = (_make_frames(frame_count=8, h=64, w=64), 24.0)
    store[secret_path] = (_make_frames(frame_count=2, h=32, w=32), 30.0)

    stego_path, meta = video_in_video.embed(cover_path, secret_path, "testkey", b=2)

    assert Path(stego_path).exists()
    assert stego_path in store
    assert meta["mode"] == "video_in_video"


def test_embed_returns_meta_keys(fake_video_io) -> None:
    store, tmp_path = fake_video_io
    cover_path = str(tmp_path / "cover.mp4")
    secret_path = str(tmp_path / "secret.mp4")

    store[cover_path] = (_make_frames(frame_count=10, h=72, w=72), 25.0)
    store[secret_path] = (_make_frames(frame_count=3, h=24, w=24), 15.0)

    _, meta = video_in_video.embed(cover_path, secret_path, "another-key", b=3)

    assert meta["mode"] == "video_in_video"
    assert isinstance(meta["secret_len"], int)
    assert meta["secret_len"] == 3 * 24 * 24 * 3
    assert meta["secret_shape"] == [24, 24, 3]
    assert meta["secret_dtype"] == "uint8"
    assert meta["b"] == 3
    assert meta["fps"] == 15.0
    assert meta["frame_count"] == 3


def test_decode_recovers_video(fake_video_io) -> None:
    store, tmp_path = fake_video_io
    cover_path = str(tmp_path / "cover.mp4")
    secret_path = str(tmp_path / "secret.mp4")

    cover_frames = _make_frames(frame_count=12, h=96, w=96)
    secret_frames = _make_frames(frame_count=4, h=32, w=32)
    store[cover_path] = (cover_frames, 24.0)
    store[secret_path] = (secret_frames, 20.0)

    key = "roundtrip-key"
    b = 3
    stego_path, meta = video_in_video.embed(cover_path, secret_path, key, b)
    recovered_path = video_in_video.decode(stego_path, key, b, meta)

    assert Path(recovered_path).exists()
    recovered_frames, recovered_fps = store[recovered_path]
    assert recovered_fps == 20.0
    assert len(recovered_frames) == len(secret_frames)
    for recovered, original in zip(recovered_frames, secret_frames):
        assert np.array_equal(recovered, original)


def test_embed_rejects_invalid_b(fake_video_io) -> None:
    store, tmp_path = fake_video_io
    cover_path = str(tmp_path / "cover.mp4")
    secret_path = str(tmp_path / "secret.mp4")

    store[cover_path] = (_make_frames(frame_count=2, h=32, w=32), 24.0)
    store[secret_path] = (_make_frames(frame_count=1, h=16, w=16), 24.0)

    for invalid_b in [0, 5, 7, -1]:
        with pytest.raises(ValueError, match="b must be in"):
            video_in_video.embed(cover_path, secret_path, "k", invalid_b)
