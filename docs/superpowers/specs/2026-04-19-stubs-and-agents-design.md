# StegoVault — Stubs + AGENTS.md Design

**Date:** 2026-04-19
**Scope:** Scaffold every empty `.py` with function signatures + docstrings + `NotImplementedError`. Add `tests/` scaffolding. Write `AGENTS.md` (agent-editing rules). Populate `requirements.txt`.

---

## Goals

1. Turn empty scaffold into typed, documented stubs so team can implement in parallel.
2. Let code-review-graph resolve real edges (imports, calls) for impact analysis.
3. Give AI agents a single-source directive file (`AGENTS.md`) for editing rules.
4. Leave room for each team member to own their module without cross-cutting rewrites.

## Non-goals

- No business logic. Every function body = `raise NotImplementedError`.
- No real tests. `tests/` gets placeholder `def test_placeholder(): pass` per module.
- No header-in-pixels self-describing stego. Metadata travels via JSON sidecar (option A).
- No changes to README.md.

---

## Module contracts

All numpy arrays are `np.uint8` unless noted. Images are `(H, W, 3)` BGR (opencv convention). Videos are `list[np.ndarray]`, each frame `(H, W, 3)`.

### `engine/spread.py`

```python
def key_to_seed(key: str) -> int:
    """MD5(key) mod 2**31. Deterministic. README-mandated."""

def get_pixel_order(seed: int, total_slots: int) -> np.ndarray:
    """np.random.default_rng(seed).permutation(total_slots). Returns int64 array."""
```

### `engine/crypto.py`

```python
def xor_bytes(data: bytes, seed: int) -> bytes:
    """XOR data with keystream from np.random.default_rng(seed). Length-preserving."""
```

### `engine/lsb.py`

```python
def embed(cover: np.ndarray, secret_bytes: bytes, b: int, seed: int) -> np.ndarray:
    """
    Overwrite bottom b LSBs of shuffled cover pixels with secret bits.
    cover: (H, W, 3) uint8. Returns same shape/dtype. Vectorized — no pixel loops.
    Raises ValueError if b not in 1..4.
    """

def decode(stego: np.ndarray, b: int, seed: int, secret_len: int) -> bytes:
    """Inverse of embed. Returns exactly secret_len bytes (still XOR-encrypted)."""
```

### `engine/capacity.py`

```python
class CapacityError(Exception):
    """Raised when secret does not fit in cover at given b."""

def check_capacity(cover_shape: tuple, b: int, secret_size: int, frame_count: int = 1) -> None:
    """
    Formula: W*H*C*frame_count*(b/8) >= secret_size.
    Raises CapacityError with human message on failure.
    """
```

### `preprocessing/image.py`

```python
def load_image(path: str) -> np.ndarray:
    """cv2.imread. PNG only. Returns (H, W, 3) uint8 BGR."""

def serialize_image(img: np.ndarray) -> tuple[bytes, dict]:
    """Flatten to raw bytes. Meta = {shape, dtype}."""

def deserialize_image(data: bytes, meta: dict) -> np.ndarray:
    """Inverse of serialize_image."""
```

### `preprocessing/video.py`

```python
def extract_frames(video_path: str) -> tuple[list[np.ndarray], float]:
    """imageio pyav plugin. Returns (frames, fps). Each frame (H, W, 3) uint8."""

def reconstruct_video(frames: list[np.ndarray], output_path: str, fps: float) -> None:
    """Lossless libx264 crf=0 preset=ultrafast pix_fmt=yuv444p via imageio.v3."""
```

### `modes/image_in_image.py`

```python
def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Load → serialize secret → XOR → capacity check → embed → save PNG. Returns (stego_path, meta)."""

def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Load stego → decode bytes → un-XOR → deserialize → save PNG. Returns output path."""
```

### `modes/image_in_video.py`

```python
def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Secret (PNG) spread across cover video frames. Returns (stego_mp4_path, meta)."""

def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Reassemble PNG from all frames. Returns output PNG path."""
```

### `modes/video_in_video.py`

```python
def embed(cover_path: str, secret_path: str, key: str, b: int) -> tuple[str, dict]:
    """Both videos. Meta carries secret fps, frame_count, per-frame shape."""

def decode(stego_path: str, key: str, b: int, meta: dict) -> str:
    """Reassemble secret MP4. Returns output path."""
```

### `ui/cache.py`

```python
def file_hash(file_bytes: bytes) -> str:
    """sha1 hex. Used as cache key."""

# + @st.cache_data wrappers around load_image / extract_frames / embed / decode per mode.
```

### `ui/capacity_meter.py`

```python
def render(cover_shape: tuple, b: int, secret_size: int, frame_count: int = 1) -> None:
    """Streamlit progress bar + % used + pass/fail badge."""
```

### `ui/preview.py`

```python
def render_frame_zero(cover_frame: np.ndarray, secret: np.ndarray, key: str, b: int) -> None:
    """Live preview of stego frame 0 for video modes. No full encode."""
```

### `ui/download.py`

```python
def offer(file_path: str, label: str, mime: str) -> None:
    """st.download_button with temp file cleanup."""
```

### `ui/demo.py`

```python
def render_bit_depth_explorer(cover: np.ndarray, secret: np.ndarray, key: str) -> None: ...
def render_key_experiment(cover: np.ndarray, secret: np.ndarray, correct_key: str) -> None: ...
def render_chi_square(stego: np.ndarray) -> None: ...
def render_psnr(cover: np.ndarray, stego: np.ndarray) -> None: ...
```

### `app.py`

```python
# Streamlit entry. Three tabs: Image→Image, Image→Video, Video→Video.
# Each tab: file uploaders, key input, b slider, capacity meter, preview, embed/decode buttons.
# + Demo panel tab calling ui/demo.py.
def main() -> None: ...
```

---

## Sidecar metadata schema

Every `embed()` returns `(stego_path, meta: dict)`. Caller writes `meta` to `<stego_path>.meta.json`. Decode loads it.

```python
{
    "mode": "image_in_image" | "image_in_video" | "video_in_video",
    "secret_len": int,          # bytes of serialized secret
    "secret_shape": [H, W, C],  # image or per-frame
    "secret_dtype": "uint8",
    "b": int,                   # 1..4
    "fps": float | None,        # only for video secret
    "frame_count": int | None,  # only for video secret
}
```

---

## Tests scaffolding

`tests/` directory with one file per module. Each contains:

```python
def test_placeholder() -> None:
    pass
```

Files: `test_spread.py`, `test_crypto.py`, `test_lsb.py`, `test_capacity.py`, `test_image_preprocessing.py`, `test_video_preprocessing.py`, `test_image_in_image.py`, `test_image_in_video.py`, `test_video_in_video.py`.

---

## AGENTS.md contents

Agent-editing rules only. No team info, no business context (README has that).

Sections:

1. **Graph-first** — always use `code-review-graph` MCP (semantic_search_nodes, query_graph, get_impact_radius, detect_changes) before Grep/Read.
2. **No new files** — scaffold is fixed. Fill existing stubs, never create.
3. **Don't touch** — `README.md`, `AGENTS.md`, other contributor's module files (see README team table).
4. **Style constraints** — numpy vectorized only, no pixel loops, cv2 for image I/O, imageio v3 pyav for video, PNG + lossless MP4, `@st.cache_data` on heavy funcs.
5. **Contracts are law** — function signatures in stubs are the spec. Don't change signatures without updating this design doc.
6. **Commit rules** — one module per commit; message format `<module>: <verb> <what>`.
7. **After edits** — run `build_or_update_graph_tool` incremental; verify edges resolved.

---

## requirements.txt

```
numpy
opencv-python
streamlit
matplotlib
imageio[ffmpeg]
pytest
```

---

## Implementation order

1. `requirements.txt`
2. `engine/` stubs (spread, crypto, lsb, capacity)
3. `preprocessing/` stubs (image, video)
4. `modes/` stubs (3 files)
5. `ui/` stubs (5 files)
6. `app.py` stub
7. `tests/` scaffolding
8. `AGENTS.md`
9. Rebuild graph, verify edge count > 0

---

## Success criteria

- Every `.py` file under `engine/`, `preprocessing/`, `modes/`, `ui/`, plus `app.py`, contains valid Python with signatures, docstrings, and `raise NotImplementedError`.
- `pytest` discovers 9 tests, all pass (placeholders).
- `AGENTS.md` exists at repo root, covers all 7 sections above.
- `build_or_update_graph_tool` reports edges > 0 and flows ≥ 1 after rebuild.
