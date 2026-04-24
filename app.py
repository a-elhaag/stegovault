"""Streamlit entry point. Three tabs: Image→Image, Image→Video, Video→Video."""

from __future__ import annotations

import json
import os

import cv2

# Allow larger video uploads (value is in MB).
os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "1024"

import streamlit as st

from ui import cache, capacity_meter, preview
from preprocessing import image as preprocess_image

_REQUIRED_META_KEYS = (
    "mode",
    "secret_len",
    "secret_shape",
    "secret_dtype",
    "b",
    "fps",
    "frame_count",
)


def _inject_styles() -> None:
    """Apply blue/white visual system for a clean app look."""
    st.markdown(
        """
        <style>
        :root {
            --sv-blue-900: #0a3d7a;
            --sv-blue-700: #1558a6;
            --sv-blue-500: #2f7fdc;
            --sv-blue-100: #eaf3ff;
            --sv-white: #ffffff;
            --sv-border: #c6dcfa;
        }
        html, body, [class*="css"] {
            font-family: "IBM Plex Sans", "Trebuchet MS", sans-serif;
        }
        .stApp {
            background:
                radial-gradient(900px 500px at 10% -10%, #d9ebff 0%, rgba(217, 235, 255, 0) 60%),
                radial-gradient(700px 420px at 100% 0%, #edf5ff 0%, rgba(237, 245, 255, 0) 55%),
                linear-gradient(180deg, #f8fbff 0%, #f3f8ff 100%);
        }
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] {
            gap: 0.8rem;
        }
        .sv-card {
            border: 1px solid var(--sv-border);
            background: var(--sv-white);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: 0 6px 20px rgba(16, 67, 137, 0.08);
        }
        .sv-card h3 {
            color: var(--sv-blue-900);
            margin: 0 0 6px 0;
            font-size: 1.05rem;
            letter-spacing: 0.01em;
        }
        .sv-note {
            color: #2b5c95;
            font-size: 0.92rem;
            margin-top: 2px;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _capacity_bytes(cover_shape: tuple[int, ...], b: int, frame_count: int = 1) -> int:
    """Mirror engine.capacity formula for UI pre-checks."""
    h, w, c = cover_shape[:3]
    return (int(w) * int(h) * int(c) * int(frame_count) * int(b)) // 8


def _parse_meta_json(meta_bytes: bytes) -> dict:
    """Parse uploaded sidecar JSON and validate required keys."""
    parsed = json.loads(meta_bytes.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("metadata file must contain a JSON object")

    missing = [k for k in _REQUIRED_META_KEYS if k not in parsed]
    if missing:
        raise ValueError(f"metadata missing keys: {', '.join(missing)}")

    return parsed


def _render_section(title: str, subtitle: str) -> None:
    st.markdown(
        (
            '<div class="sv-card">'
            f"<h3>{title}</h3>"
            f'<div class="sv-note">{subtitle}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _run_with_spinner(label: str, fn, *args, **kwargs):
    """Run a callable with a visible Streamlit loading state."""
    with st.spinner(label):
        return fn(*args, **kwargs)


def _tab_image_in_image() -> None:
    """Image-in-image tab: file uploaders, key, b slider, capacity, embed/decode."""
    _render_section(
        "Image in Image",
        "Hide a PNG secret inside a PNG cover using spread LSB and XOR.",
    )

    up_left, up_right = st.columns(2)
    with up_left:
        cover_file = st.file_uploader(
            "Cover image (PNG)",
            type=["png"],
            key="i2i_cover",
        )
    with up_right:
        secret_file = st.file_uploader(
            "Secret image (PNG)",
            type=["png"],
            key="i2i_secret",
        )

    key = st.text_input("Encryption key", key="i2i_key", type="password")
    b = st.slider("Bit depth (b)", min_value=1, max_value=4, value=2, key="i2i_b")

    cover_bytes = None
    secret_bytes = None
    secret_size = 0
    fits = False

    if cover_file and secret_file:
        cover_bytes = cover_file.getvalue()
        secret_bytes = secret_file.getvalue()

        cover_img = _run_with_spinner(
            "Loading cover image...",
            cache.cached_load_image,
            cover_bytes,
        )
        secret_img = _run_with_spinner(
            "Loading secret image...",
            cache.cached_load_image,
            secret_bytes,
        )

        preview_left, preview_right = st.columns(2)
        with preview_left:
            st.image(
                cover_img,
                caption=f"Cover preview: {cover_img.shape[1]}x{cover_img.shape[0]}",
                channels="BGR",
                width="stretch",
            )
        with preview_right:
            st.image(
                secret_img,
                caption=f"Secret preview: {secret_img.shape[1]}x{secret_img.shape[0]}",
                channels="BGR",
                width="stretch",
            )

        secret_size = len(preprocess_image.serialize_image(secret_img))
        capacity_meter.render(cover_img.shape, b, secret_size, frame_count=1)
        fits = secret_size <= _capacity_bytes(cover_img.shape, b, frame_count=1)

    embed_disabled = not (cover_file and secret_file and key and fits)
    if st.button("Embed secret", key="i2i_embed_btn", disabled=embed_disabled):
        try:
            if cover_bytes is None or secret_bytes is None:
                raise ValueError("upload both cover and secret images")

            stego_path, meta = _run_with_spinner(
                "Embedding secret into image...",
                cache.cached_embed,
                "image_in_image",
                cover_bytes,
                secret_bytes,
                key,
                b,
            )
            with open(stego_path, "rb") as f:
                stego_data = f.read()

            meta_data = json.dumps(meta, indent=2).encode("utf-8")
            st.session_state["i2i_stego_data"] = stego_data
            st.session_state["i2i_meta_data"] = meta_data
            st.success("Embedding complete.")
        except Exception as exc:
            st.error(f"Embedding failed: {exc}")

    if "i2i_stego_data" in st.session_state:
        dl_left, dl_right = st.columns(2)
        with dl_left:
            st.download_button(
                label="Download stego image",
                data=st.session_state["i2i_stego_data"],
                file_name="stego_output.png",
                mime="image/png",
                key="i2i_dl_stego",
            )
        with dl_right:
            st.download_button(
                label="Download sidecar metadata",
                data=st.session_state["i2i_meta_data"],
                file_name="stego_output.png.meta.json",
                mime="application/json",
                key="i2i_dl_meta",
            )

    st.divider()
    _render_section(
        "Decode",
        "Provide the stego PNG and matching sidecar metadata to recover the secret.",
    )

    dec_left, dec_right = st.columns(2)
    with dec_left:
        stego_file = st.file_uploader(
            "Stego image (PNG)",
            type=["png"],
            key="i2i_stego_input",
        )
    with dec_right:
        meta_file = st.file_uploader(
            "Metadata sidecar (.json)",
            type=["json"],
            key="i2i_meta_input",
        )

    decode_key = st.text_input("Key for decode", key="i2i_decode_key", type="password")

    decode_disabled = not (stego_file and meta_file and decode_key)
    if st.button("Decode secret", key="i2i_decode_btn", disabled=decode_disabled):
        try:
            if stego_file is None or meta_file is None:
                raise ValueError("upload both stego image and sidecar metadata")

            meta = _parse_meta_json(meta_file.getvalue())
            recovered_path = _run_with_spinner(
                "Decoding secret from image...",
                cache.cached_decode,
                "image_in_image",
                stego_file.getvalue(),
                decode_key,
                meta,
            )
            with open(recovered_path, "rb") as f:
                recovered_data = f.read()

            st.session_state["i2i_recovered_data"] = recovered_data
            st.success("Decoding complete.")
        except Exception as exc:
            st.error(f"Decoding failed: {exc}")

    if "i2i_recovered_data" in st.session_state:
        st.download_button(
            label="Download recovered secret",
            data=st.session_state["i2i_recovered_data"],
            file_name="recovered_secret.png",
            mime="image/png",
            key="i2i_dl_recovered",
        )


def _tab_image_in_video() -> None:
    """Image-in-video tab: file uploaders, key, b slider, frame-0 preview, embed/decode."""
    _render_section(
        "Image in Video",
        "Hide a PNG secret across video cover frames with frame-0 live preview.",
    )
    st.caption("Video upload limit: up to 1 GB per file.")

    up_left, up_right = st.columns(2)
    with up_left:
        cover_file = st.file_uploader(
            "Cover video (MP4 or MKV)",
            type=["mp4", "mkv"],
            key="i2v_cover",
            help="Maximum upload size: 1 GB.",
        )
    with up_right:
        secret_file = st.file_uploader(
            "Secret image (PNG)",
            type=["png"],
            key="i2v_secret",
        )

    key = st.text_input("Encryption key", key="i2v_key", type="password")
    b = st.slider("Bit depth (b)", min_value=1, max_value=4, value=2, key="i2v_b")

    cover_bytes = None
    secret_bytes = None
    fits = False
    grayscale_fallback = False

    if cover_file and secret_file:
        cover_bytes = cover_file.getvalue()
        secret_bytes = secret_file.getvalue()

        first_frame, fps, frame_count = _run_with_spinner(
            "Analyzing cover video for preview and capacity...",
            cache.cached_probe_video,
            cover_bytes,
        )
        secret_img = _run_with_spinner(
            "Loading secret image...",
            cache.cached_load_image,
            secret_bytes,
        )
        secret_size = int(secret_img.size * secret_img.dtype.itemsize)

        st.caption(
            f"Cover video info: {frame_count} frames at {fps:.2f} fps | "
            f"Frame size: {first_frame.shape[1]}x{first_frame.shape[0]}"
        )

        capacity_meter.render(
            cover_shape=first_frame.shape,
            b=b,
            secret_size=secret_size,
            frame_count=frame_count,
        )
        fits = secret_size <= _capacity_bytes(
            first_frame.shape, b, frame_count=frame_count
        )

        preview.render_frame_zero(first_frame, secret_img, key, b)

    embed_disabled = not (cover_file and secret_file and key and fits)
    if st.button("Embed secret", key="i2v_embed_btn", disabled=embed_disabled):
        try:
            if cover_bytes is None or secret_bytes is None:
                raise ValueError("upload both cover video and secret image")

            stego_path, meta = _run_with_spinner(
                "Embedding secret into video. This may take some time for large files...",
                cache.cached_embed,
                "image_in_video",
                cover_bytes,
                secret_bytes,
                key,
                b,
            )
            with open(stego_path, "rb") as f:
                stego_data = f.read()

            meta_data = json.dumps(meta, indent=2).encode("utf-8")
            st.session_state["i2v_stego_data"] = stego_data
            st.session_state["i2v_meta_data"] = meta_data
            st.success("Embedding complete.")
        except Exception as exc:
            st.error(f"Embedding failed: {exc}")

    if "i2v_stego_data" in st.session_state:
        dl_left, dl_right = st.columns(2)
        with dl_left:
            st.download_button(
                label="Download stego video",
                data=st.session_state["i2v_stego_data"],
                file_name="stego_output.mkv",
                mime="video/x-matroska",
                key="i2v_dl_stego",
            )
        with dl_right:
            st.download_button(
                label="Download sidecar metadata",
                data=st.session_state["i2v_meta_data"],
                file_name="stego_output.mkv.meta.json",
                mime="application/json",
                key="i2v_dl_meta",
            )

    st.divider()
    _render_section(
        "Decode",
        "Provide the stego video and matching sidecar metadata to recover the secret image.",
    )

    dec_left, dec_right = st.columns(2)
    with dec_left:
        stego_file = st.file_uploader(
            "Stego video (MKV or MP4)",
            type=["mkv", "mp4"],
            key="i2v_stego_input",
            help="Maximum upload size: 1 GB.",
        )
    with dec_right:
        meta_file = st.file_uploader(
            "Metadata sidecar (.json)",
            type=["json"],
            key="i2v_meta_input",
        )

    decode_key = st.text_input("Key for decode", key="i2v_decode_key", type="password")

    decode_disabled = not (stego_file and meta_file and decode_key)
    if st.button("Decode secret", key="i2v_decode_btn", disabled=decode_disabled):
        try:
            if stego_file is None or meta_file is None:
                raise ValueError("upload both stego video and sidecar metadata")

            meta = _parse_meta_json(meta_file.getvalue())
            recovered_path = _run_with_spinner(
                "Decoding secret from video. This may take some time for large files...",
                cache.cached_decode,
                "image_in_video",
                stego_file.getvalue(),
                decode_key,
                meta,
                stego_file.name,
            )
            with open(recovered_path, "rb") as f:
                recovered_data = f.read()

            st.session_state["i2v_recovered_data"] = recovered_data
            st.success("Decoding complete.")
        except Exception as exc:
            st.error(f"Decoding failed: {exc}")

    if "i2v_recovered_data" in st.session_state:
        st.download_button(
            label="Download recovered secret",
            data=st.session_state["i2v_recovered_data"],
            file_name="recovered_secret.png",
            mime="image/png",
            key="i2v_dl_recovered",
        )


def _tab_video_in_video() -> None:
    """Video-in-video tab: file uploaders, key, b slider, preview, embed/decode."""
    _render_section(
        "Video in Video",
        "Hide a video secret inside a video cover using lossless LSB embedding and XOR.",
    )
    st.caption("Video-in-video upload limit: up to 1 GB per file.")

    up_left, up_right = st.columns(2)
    with up_left:
        cover_file = st.file_uploader(
            "Cover video (MP4 or MKV, up to 1 GB)",
            type=["mp4", "mkv"],
            key="v2v_cover",
            help="Maximum upload size: 1 GB.",
        )
    with up_right:
        secret_file = st.file_uploader(
            "Secret video (MP4 or MKV, up to 1 GB)",
            type=["mp4", "mkv"],
            key="v2v_secret",
            help="Maximum upload size: 1 GB.",
        )

    key = st.text_input("Encryption key", key="v2v_key", type="password")
    b = st.slider("Bit depth (b)", min_value=1, max_value=4, value=2, key="v2v_b")

    cover_bytes = None
    secret_bytes = None
    fits = False

    if cover_file and secret_file:
        cover_bytes = cover_file.getvalue()
        secret_bytes = secret_file.getvalue()

        cover_first_frame, cover_fps, cover_frame_count = _run_with_spinner(
            "Analyzing cover video for preview and capacity...",
            cache.cached_probe_video,
            cover_bytes,
        )
        secret_first_frame, secret_fps, secret_frame_count = _run_with_spinner(
            "Analyzing secret video...",
            cache.cached_probe_video,
            secret_bytes,
        )

        st.caption(
            f"Cover video info: {cover_frame_count} frames at {cover_fps:.2f} fps | "
            f"Frame size: {cover_first_frame.shape[1]}x{cover_first_frame.shape[0]}"
        )
        st.caption(
            f"Secret video info: {secret_frame_count} frames at {secret_fps:.2f} fps | "
            f"Frame size: {secret_first_frame.shape[1]}x{secret_first_frame.shape[0]}"
        )

        if secret_frame_count > cover_frame_count:
            st.warning(
                "The secret has more frames than the cover. Embedding can still proceed "
                "if the byte capacity fits, but the temporal ratio is denser than the cover."
            )

        secret_preview = cv2.resize(
            secret_first_frame,
            (cover_first_frame.shape[1], cover_first_frame.shape[0]),
            interpolation=cv2.INTER_AREA,
        )

        color_secret_size = int(
            secret_frame_count
            * cover_first_frame.shape[0]
            * cover_first_frame.shape[1]
            * cover_first_frame.shape[2]
        )
        gray_secret_size = int(
            secret_frame_count * cover_first_frame.shape[0] * cover_first_frame.shape[1]
        )
        chosen_size = color_secret_size
        if color_secret_size <= _capacity_bytes(
            cover_first_frame.shape, b, frame_count=cover_frame_count
        ):
            fits = True
        elif gray_secret_size <= _capacity_bytes(
            cover_first_frame.shape, b, frame_count=cover_frame_count
        ):
            fits = True
            grayscale_fallback = True
            chosen_size = gray_secret_size
            st.info(
                "The color version does not fit, but the secret will be auto-converted to grayscale and can be embedded."
            )
        capacity_meter.render(
            cover_shape=cover_first_frame.shape,
            b=b,
            secret_size=chosen_size,
            frame_count=cover_frame_count,
        )

        preview.render_frame_zero(cover_first_frame, secret_preview, key, b)

    embed_disabled = not (cover_file and secret_file and key and fits)
    if st.button("Embed secret", key="v2v_embed_btn", disabled=embed_disabled):
        try:
            if cover_bytes is None or secret_bytes is None:
                raise ValueError("upload both cover video and secret video")

            stego_path, meta = _run_with_spinner(
                "Embedding secret into video. This may take some time for large files...",
                cache.cached_embed,
                "video_in_video",
                cover_bytes,
                secret_bytes,
                key,
                b,
            )
            with open(stego_path, "rb") as f:
                stego_data = f.read()

            meta_data = json.dumps(meta, indent=2).encode("utf-8")
            st.session_state["v2v_stego_data"] = stego_data
            st.session_state["v2v_meta_data"] = meta_data
            st.success("Embedding complete.")
        except Exception as exc:
            st.error(f"Embedding failed: {exc}")

    if "v2v_stego_data" in st.session_state:
        dl_left, dl_right = st.columns(2)
        with dl_left:
            st.download_button(
                label="Download stego video",
                data=st.session_state["v2v_stego_data"],
                file_name="stego_output.mkv",
                mime="video/x-matroska",
                key="v2v_dl_stego",
            )
        with dl_right:
            st.download_button(
                label="Download sidecar metadata",
                data=st.session_state["v2v_meta_data"],
                file_name="stego_output.mkv.meta.json",
                mime="application/json",
                key="v2v_dl_meta",
            )

    st.divider()
    _render_section(
        "Decode",
        "Provide the stego video and matching sidecar metadata to recover the secret video.",
    )

    dec_left, dec_right = st.columns(2)
    with dec_left:
        stego_file = st.file_uploader(
            "Stego video (MKV or MP4, up to 1 GB)",
            type=["mkv", "mp4"],
            key="v2v_stego_input",
            help="Maximum upload size: 1 GB.",
        )
    with dec_right:
        meta_file = st.file_uploader(
            "Metadata sidecar (.json)",
            type=["json"],
            key="v2v_meta_input",
        )

    decode_key = st.text_input("Key for decode", key="v2v_decode_key", type="password")

    decode_disabled = not (stego_file and meta_file and decode_key)
    if st.button("Decode secret", key="v2v_decode_btn", disabled=decode_disabled):
        try:
            if stego_file is None or meta_file is None:
                raise ValueError("upload both stego video and sidecar metadata")

            meta = _parse_meta_json(meta_file.getvalue())
            recovered_path = _run_with_spinner(
                "Decoding secret from video. This may take some time for large files...",
                cache.cached_decode,
                "video_in_video",
                stego_file.getvalue(),
                decode_key,
                meta,
                stego_file.name,
            )
            with open(recovered_path, "rb") as f:
                recovered_data = f.read()

            st.session_state["v2v_recovered_data"] = recovered_data
            st.success("Decoding complete.")
        except Exception as exc:
            st.error(f"Decoding failed: {exc}")

    if "v2v_recovered_data" in st.session_state:
        st.download_button(
            label="Download recovered secret",
            data=st.session_state["v2v_recovered_data"],
            file_name="recovered_secret.mkv",
            mime="video/x-matroska",
            key="v2v_dl_recovered",
        )


def main() -> None:
    """Configure page, render four-tab layout."""
    st.set_page_config(
        page_title="StegoVault",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_styles()

    st.title("StegoVault")
    st.caption("Secure steganography workflows for image and video covers")

    tab_i2i, tab_i2v, tab_v2v = st.tabs(
        ["Image to Image", "Image to Video", "Video to Video"]
    )

    with tab_i2i:
        _tab_image_in_image()
    with tab_i2v:
        _tab_image_in_video()
    with tab_v2v:
        _tab_video_in_video()


if __name__ == "__main__":
    main()
