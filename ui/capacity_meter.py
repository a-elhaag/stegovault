"""Live capacity progress bar component."""

from __future__ import annotations

import streamlit as st


def render(cover_shape: tuple, b: int, secret_size: int, frame_count: int = 1) -> None:
    """Show st.progress bar + % used + pass/fail badge.

    Reads capacity formula: W * H * C * frame_count * (b / 8).
    Green badge if secret fits, red badge otherwise.
    """
    if b not in range(1, 5):
        st.error("Bit depth must be in range 1 to 4.")
        return

    if len(cover_shape) < 3:
        st.error("Invalid cover shape for capacity calculation.")
        return

    h, w, c = (int(cover_shape[0]), int(cover_shape[1]), int(cover_shape[2]))
    frames = max(1, int(frame_count))
    needed = max(0, int(secret_size))

    capacity_bytes = (w * h * c * frames * b) // 8
    if capacity_bytes <= 0:
        st.error("Cover capacity is zero for the current settings.")
        return

    usage_ratio = needed / capacity_bytes
    fits = needed <= capacity_bytes

    st.progress(float(min(1.0, usage_ratio)))

    left, right = st.columns(2)
    with left:
        st.caption(
            f"Secret size: {needed:,} bytes | Capacity: {capacity_bytes:,} bytes"
        )
    with right:
        st.caption(f"Usage: {usage_ratio * 100:.1f}%")

    if fits:
        st.success("Capacity status: secret fits in cover.")
    else:
        st.error("Capacity status: secret exceeds available cover capacity.")
