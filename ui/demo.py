"""Interactive demo panel: bit-depth explorer, key experiment, chi-square, PSNR."""

from __future__ import annotations

import numpy as np
import streamlit as st


def render_bit_depth_explorer(cover: np.ndarray, secret: np.ndarray, key: str) -> None:
    """Show stego output side-by-side for b=1,2,3,4 with live PSNR per depth."""
    raise NotImplementedError


def render_key_experiment(cover: np.ndarray, secret: np.ndarray, correct_key: str) -> None:
    """Try multiple keys. Correct key shows clean secret; wrong key shows noise."""
    raise NotImplementedError


def render_chi_square(stego: np.ndarray) -> None:
    """Display chi-square steganalysis score before and after embed. Color-coded badge."""
    raise NotImplementedError


def render_psnr(cover: np.ndarray, stego: np.ndarray) -> None:
    """Display PSNR dB value, max/mean delta, per-channel R/G/B breakdown."""
    raise NotImplementedError
