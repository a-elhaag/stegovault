"""Live capacity progress bar component."""

from __future__ import annotations

import streamlit as st


def render(cover_shape: tuple, b: int, secret_size: int, frame_count: int = 1) -> None:
    """Show st.progress bar + % used + pass/fail badge.

    Reads capacity formula: W * H * C * frame_count * (b / 8).
    Green badge if secret fits, red badge otherwise.
    """
    raise NotImplementedError
