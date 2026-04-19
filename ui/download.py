"""Download button with temp file cleanup."""

from __future__ import annotations

import os
import streamlit as st


def offer(file_path: str, label: str, mime: str) -> None:
    """Render st.download_button for file_path. Cleans up temp file after download."""
    raise NotImplementedError
    if not os.path.exists(file_path):
        return

    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except OSError:
        return

    st.download_button(
        label=label,
        data=file_bytes,
        file_name=os.path.basename(file_path),
        mime=mime,
    )

    try:
        os.unlink(file_path)
    except OSError:
        pass
