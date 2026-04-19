"""Frame-0 live preview for video modes. No full encode on slider move."""

from __future__ import annotations

import numpy as np
import streamlit as st


def render_frame_zero(
    cover_frame: np.ndarray,
    secret: np.ndarray,
    key: str,
    b: int,
) -> None:
    """Embed secret into frame 0 only and display side-by-side with cover.

    Called on slider interaction. Full encode only happens on button click.
    """
    raise NotImplementedError
