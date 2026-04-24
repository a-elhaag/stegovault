# StegoVault

A steganography tool that hides images and videos inside other images or videos using LSB embedding with spread spectrum scrambling and XOR encryption, exposed via a Streamlit UI with an interactive demo panel.

---

## Modes

| Mode | Cover | Secret |
|------|-------|--------|
| Image → Image | PNG | PNG |
| Image → Video | MP4/MKV (lossless) | PNG |
| Video → Video | MP4/MKV (lossless) | MP4/MKV |

---

## Algorithm

1. Flatten secret data to raw bytes
2. XOR bytes with keystream derived from `key_to_seed(key)`
3. Shuffle pixel indices using same seed (spread spectrum)
4. Write encrypted bits into the bottom `b` LSBs of shuffled cover pixels
5. Reconstruct cover with modified pixels → lossless save

Decode is steps 5→1 reversed with same key.

**Bit depth `b` (1–4)** controls how many LSBs of the cover are overwritten and how many MSBs of the secret are injected. Same value governs both sides.

---

## Project structure

```
stegovault/
├── engine/
│   ├── __init__.py
│   ├── spread.py         # get_pixel_order(seed, total_slots) → np.ndarray
│   ├── crypto.py         # xor_bytes(data, seed) → bytes
│   ├── lsb.py            # embed(cover, secret_bytes, b, seed) / decode(stego, b, seed, secret_len)
│   └── capacity.py       # check_capacity(cover_shape, b, secret_size, frame_count) / CapacityError
│
├── preprocessing/
│   ├── __init__.py
│   ├── image.py          # load_image / serialize_image / deserialize_image
│   └── video.py          # extract_frames / reconstruct_video
│
├── modes/
│   ├── __init__.py
│   ├── image_in_image.py # embed(cover, secret, key, b) / decode(stego, key, meta)
│   ├── image_in_video.py # embed(cover, secret, key, b) / decode(stego, key, meta)
│   └── video_in_video.py # embed(cover, secret, key, b) / decode(stego, key, meta)
│
├── ui/
│   ├── __init__.py
│   ├── cache.py          # @st.cache_data wrappers + file_hash()
│   ├── capacity_meter.py # live capacity % component
│   ├── preview.py        # frame 0 live preview for video modes
│   ├── download.py       # download button + temp file handling
│   └── demo.py           # key experiment / chi-square / PSNR / bit depth explorer
│
├── app.py                # Streamlit entry point, three mode tabs
└── requirements.txt
```

---

## Setup

### 1. Scaffold the project

```bash
mkdir -p stegovault/{engine,preprocessing,modes,ui} && \
touch stegovault/engine/{__init__.py,spread.py,crypto.py,lsb.py,capacity.py} && \
touch stegovault/preprocessing/{__init__.py,image.py,video.py} && \
touch stegovault/modes/{__init__.py,image_in_image.py,image_in_video.py,video_in_video.py} && \
touch stegovault/ui/{__init__.py,cache.py,capacity_meter.py,preview.py,download.py,demo.py} && \
touch stegovault/app.py stegovault/requirements.txt stegovault/README.md
```

### 2. Install dependencies

```bash
pip install numpy opencv-python streamlit matplotlib imageio[ffmpeg]
```

No system FFmpeg install needed. `imageio[ffmpeg]` downloads the FFmpeg binary automatically — works locally and on Streamlit Cloud.

### 3. Run locally

```bash
streamlit run app.py
```

---

## Requirements

```
numpy
opencv-python
streamlit
matplotlib
imageio[ffmpeg]
```

All pure Python — no system dependencies. FFmpeg binary is bundled via `imageio[ffmpeg]`.

---

## Deployment — Streamlit Cloud

1. Push repo to GitHub
2. Go to share.streamlit.io
3. Set main file path to `app.py`
4. Streamlit Cloud installs `requirements.txt` automatically — no extra config needed
5. No `packages.txt` required since FFmpeg is handled by `imageio[ffmpeg]`

---

## Key derivation

All modes use this exact function — no variation:

```python
import hashlib

def key_to_seed(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2 ** 31)
```

---

## Capacity formula

$$C = W \times H \times C_{channels} \times F \times \frac{b}{8} \geq |secret\_bytes|$$

Embed raises `CapacityError` before starting if constraint is not satisfied.

---

## Critical rules for contributors

- **No new files.** All files are pre-created. Write into existing files only.
- **PNG only for images.** JPEG destroys LSBs on save.
- **Lossless video only.** Always use `-crf 0 -preset ultrafast -pix_fmt yuv444p` via `imageio[ffmpeg]`.
- **`opencv-python` only for image I/O.** No Pillow.
- **`numpy` only for bit ops.** No Python loops over pixels.
- **Spread spectrum on every embed.** Never sequential LSB.
- **XOR encryption on every embed.** Never embed plaintext bits.
- **Capacity check before every embed.**
- **`@st.cache_data` on every heavy function.**
- **Video modes: frame 0 preview on slider, full encode on button click only.**
- **FFmpeg via `imageio.get_writer` / `imageio.get_reader` only.** No subprocess calls.

---

## Video I/O pattern

`preprocessing/video.py` uses `imageio.v3` with `plugin="pyav"`. Codec is selected by output extension:

| Output ext | Codec | Pixel format | Notes |
|------------|-------|--------------|-------|
| `.mkv` | `ffv1` | `bgr0` | Byte-exact lossless — recommended for steganography |
| `.mp4` | `libx264` crf=0 | `yuv444p` | Theoretically lossless; not guaranteed for LSB payloads |

**Warning:** H.264 treats LSB payloads (pseudorandom noise) as compression artifacts and may corrupt them. Use MKV/FFV1 for any mode that embeds in video pixels.

Key functions in `preprocessing/video.py`:

```python
extract_frames(video_path)          # → (list[ndarray], fps)
extract_frame_stack(video_path)     # → (ndarray F×H×W×3, fps) — pre-allocated, lower peak memory
extract_partial_frame_stack(video_path, num_frames)  # → (ndarray, fps) — early exit
probe_video(video_path)             # → (first_frame, fps, frame_count) — O(1) memory
reconstruct_video(frames, output_path, fps)  # codec auto-selected by extension
```

---

## Team

| Member | Owns |
|--------|------|
| Anas | `engine/`, `preprocessing/video.py`, `ui/`, `app.py` |
| Sohaila | `preprocessing/image.py`, `modes/image_in_image.py` |
| Youmna | `modes/image_in_video.py` |
| Youstina | `modes/video_in_video.py` |

---

## Demo panel features

- **Bit depth explorer** — side-by-side output at b=1,2,3,4 with live PSNR per depth
- **Key experiment** — try multiple keys, correct key shows clean secret, wrong key shows noise
- **Chi-square score** — steganalysis score before and after embed, color-coded badge
- **PSNR metric** — dB value, max/mean delta, per-channel R/G/B breakdown

---

## Perceptual impact

| b (bits) | Max pixel delta | Approx. PSNR | Visible? |
|----------|----------------|--------------|---------|
| 1 | ±1 | ~51 dB | No |
| 2 | ±3 | ~44 dB | No |
| 3 | ±7 | ~37 dB | Barely |
| 4 | ±15 | ~30 dB | Possibly |

---

## License

MIT