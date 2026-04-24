"""Tests for modes.image_in_image: embed, decode."""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from modes.image_in_image import decode, embed


def create_test_png(path: str, shape: tuple) -> None:
    """Helper to create a test PNG image."""
    img = np.random.randint(0, 256, shape, dtype=np.uint8)
    cv2.imwrite(path, img)


def test_embed_creates_stego_file() -> None:
    """Test that embed creates a stego file and returns valid path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test images
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        create_test_png(cover_path, (200, 200, 3))
        create_test_png(secret_path, (50, 50, 3))
        
        # Embed
        stego_path, meta = embed(cover_path, secret_path, "testkey", b=2)
        
        # Verify stego file exists and is readable
        assert Path(stego_path).exists()
        stego = cv2.imread(stego_path)
        assert stego is not None
        assert stego.dtype == np.uint8


def test_embed_returns_meta_keys() -> None:
    """Test that embed returns metadata dict with all required keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        create_test_png(cover_path, (100, 100, 3))
        create_test_png(secret_path, (40, 40, 3))
        
        stego_path, meta = embed(cover_path, secret_path, "testkey", b=2)
        
        # Check all required metadata keys
        assert "mode" in meta
        assert meta["mode"] == "image_in_image"
        assert "secret_len" in meta
        assert isinstance(meta["secret_len"], int)
        assert meta["secret_len"] > 0
        assert "secret_shape" in meta
        assert isinstance(meta["secret_shape"], list)
        assert meta["secret_shape"] == [40, 40, 3]
        assert "secret_dtype" in meta
        assert meta["secret_dtype"] == "uint8"
        assert "b" in meta
        assert meta["b"] == 2
        assert "fps" in meta
        assert meta["fps"] is None
        assert "frame_count" in meta
        assert meta["frame_count"] is None


def test_decode_recovers_secret() -> None:
    """Test that decode recovers the secret image exactly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        # Create test images with known content
        original_secret = np.array(
            [[[100, 150, 200], [50, 75, 100]], [[200, 100, 50], [25, 75, 150]]],
            dtype=np.uint8,
        )
        cover = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        
        cv2.imwrite(cover_path, cover)
        cv2.imwrite(secret_path, original_secret)
        
        key = "testkey123"
        b = 2
        
        # Embed
        stego_path, meta = embed(cover_path, secret_path, key, b)
        
        # Decode
        recovered_path = decode(stego_path, key, meta)
        
        # Load recovered secret and verify
        recovered_secret = cv2.imread(recovered_path)
        assert recovered_secret is not None
        assert recovered_secret.shape == original_secret.shape
        assert recovered_secret.dtype == original_secret.dtype
        assert np.array_equal(recovered_secret, original_secret)


def test_wrong_key_does_not_recover() -> None:
    """Test that using wrong key produces garbage, not valid data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        original_secret = np.array(
            [[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8
        )
        cover = np.random.randint(0, 256, (150, 150, 3), dtype=np.uint8)
        
        cv2.imwrite(cover_path, cover)
        cv2.imwrite(secret_path, original_secret)
        
        key = "correctkey"
        wrong_key = "wrongkey"
        b = 2
        
        # Embed with correct key
        stego_path, meta = embed(cover_path, secret_path, key, b)
        
        # Decode with wrong key should fail because garbage bytes won't be valid PNG
        with pytest.raises(ValueError):
            decode(stego_path, wrong_key, meta)


def test_embed_respects_b_value() -> None:
    """Test that embed works with different b values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        create_test_png(cover_path, (150, 150, 3))
        create_test_png(secret_path, (30, 30, 3))
        
        # Test each valid b value
        for b in [1, 2, 3, 4]:
            stego_path, meta = embed(cover_path, secret_path, "testkey", b)
            assert meta["b"] == b
            assert Path(stego_path).exists()
            
            # Verify we can decode it
            recovered_path = decode(stego_path, "testkey", meta)
            assert Path(recovered_path).exists()


def test_embed_rejects_invalid_b() -> None:
    """Test that embed raises ValueError for invalid b values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cover_path = str(Path(tmpdir) / "cover.png")
        secret_path = str(Path(tmpdir) / "secret.png")
        
        create_test_png(cover_path, (100, 100, 3))
        create_test_png(secret_path, (40, 40, 3))
        
        # Test invalid b values
        for invalid_b in [0, 5, 10, -1]:
            with pytest.raises(ValueError, match="b must be in"):
                embed(cover_path, secret_path, "testkey", invalid_b)
