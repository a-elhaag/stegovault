"""Download button with temp file cleanup."""

from __future__ import annotations

import streamlit as st


def offer(file_path: str, label: str, mime: str) -> None:
    """Render st.download_button for file_path. Cleans up temp file after download."""
    raise NotImplementedError
