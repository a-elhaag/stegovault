"""Capacity guardrail — fail before expensive embed work."""

from __future__ import annotations


class CapacityError(Exception):
    """Raised when secret size exceeds available cover capacity."""
    pass


def check_capacity(
    cover_shape: tuple,
    b: int,
    secret_size: int,
    frame_count: int = 1,
) -> None:
    """Validate that cover has enough capacity for secret.
    
    Calculates available LSB capacity and raises CapacityError if secret
    is too large. Always call before embed() to fail fast.
    
    Capacity formula:
        capacity_bytes = (H * W * C * frame_count * b) // 8
        
    Where:
        H, W, C = cover image height, width, channels (uint8)
        frame_count = 1 for images, >1 for video
        b = bit depth [1, 4]
    
    Args:
        cover_shape: tuple (H, W, C) or (frames, H, W, C) of uint8 array.
        b: bit depth [1, 4].
        secret_size: byte length of serialized secret (must be accurate).
        frame_count: number of frames (default 1 for images, >1 for video).
    
    Raises:
        CapacityError: if secret_size > capacity_bytes.
    
    Examples:
        >>> check_capacity((480, 640, 3), b=2, secret_size=10000)  # OK
        >>> check_capacity((480, 640, 3), b=2, secret_size=1000000)  # Raises
    """
    H, W, C = cover_shape[:3]
    capacity_bytes = (W * H * C * frame_count * b) // 8
    if capacity_bytes < secret_size:
        raise CapacityError(
            f"Secret ({secret_size:,} bytes) exceeds cover capacity "
            f"({capacity_bytes:,} bytes) at b={b}, frames={frame_count}. "
            f"Reduce secret size, increase b, or use a larger cover."
        )
