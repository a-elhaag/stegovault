"""Frame-0 live preview for video modes. No full encode on slider move."""

from __future__ import annotations

import cv2
import numpy as np
import streamlit as st

from engine import capacity, crypto, lsb, spread
from preprocessing import image


def render_frame_zero(
    cover_frame: np.ndarray,
    secret: np.ndarray,
    key: str,
    b: int,
) -> None:
    """Embed secret into frame 0 only and display side-by-side with cover.

    Called on slider interaction. Full encode only happens on button click.
    """
    if cover_frame.dtype != np.uint8 or cover_frame.ndim != 3 or cover_frame.shape[2] != 3:
        st.error("Preview requires a cover frame with shape (H, W, 3) and dtype uint8.")
        return

    if secret.dtype != np.uint8 or secret.ndim != 3 or secret.shape[2] != 3:
        st.error("Preview requires a secret image with shape (H, W, 3) and dtype uint8.")
        return

    if b not in range(1, 5):
        st.error("Bit depth must be in range 1 to 4.")
        return

    try:
        secret_bytes = image.serialize_image(secret)
    except NotImplementedError:
        ok, encoded = cv2.imencode(".png", secret)
        if not ok:
            st.error("Unable to encode secret image for preview.")
            return
        secret_bytes = encoded.tobytes()

    try:
        capacity.check_capacity(cover_frame.shape, b, len(secret_bytes), frame_count=1)
    except capacity.CapacityError:
        st.warning("Frame-0 preview unavailable: secret does not fit in one frame at this bit depth.")
        return

    seed = spread.key_to_seed(key)
    encrypted = crypto.xor_bytes(secret_bytes, seed)

    stego_frame = lsb.embed(cover_frame, encrypted, b, seed)

    st.caption("Frame-0 preview only. Full encode runs when you click Embed.")
    col_cover, col_stego = st.columns(2)
    with col_cover:
        st.image(cover_frame, caption="Cover frame 0", channels="BGR", width="stretch")
    with col_stego:
        st.image(stego_frame, caption=f"Preview stego frame 0 (b={b})", channels="BGR", width="stretch")
