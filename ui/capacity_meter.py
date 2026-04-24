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

    pct = min(100.0, usage_ratio * 100)
    bar_color = "#62b6cb" if pct < 70 else ("#5fa8d3" if pct < 90 else "#1b4965")
    status_label = "Fits" if fits else "Exceeds capacity"

    st.markdown(
        f"""
        <div class="sv-capacity-wrap">
            <div class="sv-capacity-header">
                <span class="sv-capacity-title">Capacity</span>
                <span class="sv-capacity-pct" style="color:{bar_color}">
                    {pct:.1f}% &mdash; {status_label}
                </span>
            </div>
            <div class="sv-capacity-track">
                <div class="sv-capacity-fill" style="
                    width:{pct}%;
                    background:{bar_color};
                    box-shadow:0 0 8px {bar_color}88;
                    transition:width 0.4s ease;
                "></div>
            </div>
            <div class="sv-capacity-info">
                {needed:,} bytes needed &nbsp;&middot;&nbsp; {capacity_bytes:,} bytes available
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
