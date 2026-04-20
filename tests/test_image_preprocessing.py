"""Tests for preprocessing.image: load_image, serialize_image, deserialize_image."""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from preprocessing.image import deserialize_image, load_image, serialize_image


def test_serialize_deserialize_roundtrip() -> None:
    """Test that serialize -> deserialize recovers the original image."""
    # Create a test image
    original = np.array(
        [[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [128, 128, 128]]],
        dtype=np.uint8,
    )

    # Serialize and deserialize
    data = serialize_image(original)
    recovered = deserialize_image(data)

    # Check shape and dtype match
    assert recovered.shape == original.shape
    assert recovered.dtype == original.dtype

    # Check values match (PNG is lossless)
    assert np.array_equal(recovered, original)


def test_serialize_meta_keys() -> None:
    """Test that serialize returns bytes."""
    img = np.ones((10, 10, 3), dtype=np.uint8)
    data = serialize_image(img)

    # Should return bytes
    assert isinstance(data, bytes)
    # Should be PNG-encoded (starts with PNG magic number)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_load_image_returns_uint8() -> None:
    """Test that load_image returns uint8 array."""
    # Create a temporary PNG file
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.png"
        test_img = np.array(
            [[[100, 150, 200], [50, 75, 100]]], dtype=np.uint8
        )
        cv2.imwrite(str(path), test_img)

        # Load the image
        loaded = load_image(str(path))

        # Check dtype and shape
        assert loaded.dtype == np.uint8
        assert loaded.shape == test_img.shape

        # Check values
        assert np.array_equal(loaded, test_img)


def test_load_image_nonexistent_file() -> None:
    """Test that load_image raises ValueError for nonexistent file."""
    with pytest.raises(ValueError, match="Could not load image"):
        load_image("/nonexistent/path/to/image.png")


def test_deserialize_invalid_data() -> None:
    """Test that deserialize_image raises ValueError for invalid PNG data."""
    with pytest.raises(ValueError, match="Failed to decode PNG data"):
        deserialize_image(b"not a valid PNG")


def test_serialize_various_shapes() -> None:
    """Test serialize with various image shapes."""
    # Single pixel
    img1 = np.array([[[255, 0, 0]]], dtype=np.uint8)
    data1 = serialize_image(img1)
    recovered1 = deserialize_image(data1)
    assert np.array_equal(recovered1, img1)

    # Large image
    img2 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    data2 = serialize_image(img2)
    recovered2 = deserialize_image(data2)
    assert np.array_equal(recovered2, img2)

    # Tall image
    img3 = np.random.randint(0, 256, (200, 50, 3), dtype=np.uint8)
    data3 = serialize_image(img3)
    recovered3 = deserialize_image(data3)
    assert np.array_equal(recovered3, img3)


def test_load_image_with_actual_file() -> None:
    """Test load_image with a created PNG file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_img.png"

        # Create and save a test image
        original = np.array(
            [[[10, 20, 30], [40, 50, 60]], [[70, 80, 90], [100, 110, 120]]],
            dtype=np.uint8,
        )
        cv2.imwrite(str(path), original)

        # Load it back
        loaded = load_image(str(path))

        # Verify
        assert np.array_equal(loaded, original)
