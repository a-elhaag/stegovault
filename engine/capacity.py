"""Capacity guardrail — fail before expensive embed work."""

from __future__ import annotations

def check_capacity(
    cover_shape: tuple,
    b: int,
    secret_size: int,
    frame_count: int = 1,
) -> None:
    H, W, C = cover_shape[:3]
    capacity_bytes = (W * H * C * frame_count * b) // 8
    if capacity_bytes < secret_size:
        raise CapacityError(
            f"Secret ({secret_size:,} bytes) exceeds cover capacity "
            f"({capacity_bytes:,} bytes) at b={b}, frames={frame_count}. "
            f"Reduce secret size, increase b, or use a larger cover."
        )
