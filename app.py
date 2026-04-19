"""Streamlit entry point. Four tabs: Image→Image, Image→Video, Video→Video, Demo."""

from __future__ import annotations

import streamlit as st

from modes import image_in_image, image_in_video, video_in_video
from ui import cache, capacity_meter, demo, download, preview


def _tab_image_in_image() -> None:
    """Image-in-image tab: file uploaders, key, b slider, capacity, embed/decode."""
    raise NotImplementedError


def _tab_image_in_video() -> None:
    """Image-in-video tab: file uploaders, key, b slider, frame-0 preview, embed/decode."""
    raise NotImplementedError


def _tab_video_in_video() -> None:
    """Video-in-video tab: file uploaders, key, b slider, frame-0 preview, embed/decode."""
    raise NotImplementedError


def _tab_demo() -> None:
    """Demo panel tab: calls ui.demo render functions."""
    raise NotImplementedError


def main() -> None:
    """Configure page, render four-tab layout."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
