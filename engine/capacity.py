"""Capacity guardrail — fail before expensive embed work."""

from __future__ import annotations


class CapacityError(Exception):
    """Raised when secret does not fit in cover at the requested bit depth."""


def check_capacity(
    cover_shape: tuple,
    b: int,
    secret_size: int,
    frame_count: int = 1,
) -> None:
    """Raise CapacityError if secret won't fit.

    Formula: W * H * C * frame_count * (b / 8) >= secret_size.
    cover_shape: shape of one frame, e.g. (H, W, 3).
    Raises CapacityError with human-readable message on failure.
    """
    H, W, C = cover_shape[:3]
    capacity_bytes = int(W * H * C * frame_count * b / 8)
    if capacity_bytes < secret_size:
        raise CapacityError(
            f"Secret ({secret_size:,} bytes) exceeds cover capacity "
            f"({capacity_bytes:,} bytes) at b={b}, frames={frame_count}. "
            f"Reduce secret size, increase b, or use a larger cover."
        )
