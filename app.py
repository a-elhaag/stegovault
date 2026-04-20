"""Streamlit entry point. Four tabs: Image→Image, Image→Video, Video→Video, Demo."""

from __future__ import annotations

import json

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
    decode_b = st.slider(
        "Bit depth used during embed",
        min_value=1,
        max_value=4,
        value=2,
        key="i2i_decode_b",
    )

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
                decode_b,
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

    up_left, up_right = st.columns(2)
    with up_left:
        cover_file = st.file_uploader(
            "Cover video (MP4)",
            type=["mp4"],
            key="i2v_cover",
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
        fits = secret_size <= _capacity_bytes(first_frame.shape, b, frame_count=frame_count)

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
        )
    with dec_right:
        meta_file = st.file_uploader(
            "Metadata sidecar (.json)",
            type=["json"],
            key="i2v_meta_input",
        )

    decode_key = st.text_input("Key for decode", key="i2v_decode_key", type="password")
    decode_b = st.slider(
        "Bit depth used during embed",
        min_value=1,
        max_value=4,
        value=2,
        key="i2v_decode_b",
    )

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
                decode_b,
                meta,
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
    """Video-in-video tab: file uploaders, key, b slider, frame-0 preview, embed/decode."""
    _render_section(
        "Video in Video",
        "This tab is intentionally disabled while the mode pipeline is still under implementation.",
    )
    st.info("Video-in-video processing is not enabled yet. Use Image in Image or Image in Video for now.")


def _tab_demo() -> None:
    """Demo panel tab: calls ui.demo render functions."""
    _render_section(
        "Demo Panel",
        "Interactive analytics widgets are temporarily disabled until demo components are implemented.",
    )
    st.info("Demo widgets are not enabled yet. Core embed/decode workflows are available in the first two tabs.")


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

    tab_i2i, tab_i2v, tab_v2v, tab_demo = st.tabs(
        ["Image to Image", "Image to Video", "Video to Video", "Demo"]
    )

    with tab_i2i:
        _tab_image_in_image()
    with tab_i2v:
        _tab_image_in_video()
    with tab_v2v:
        _tab_video_in_video()
    with tab_demo:
        _tab_demo()


if __name__ == "__main__":
    main()
