# AGENTS.md — AI Agent Editing Rules for StegoVault

Rules for any AI agent (Claude, Copilot, Cursor, etc.) editing this repo.
Human team rules live in README.md.

---

## 1. Graph first

Before reading any file, always query the code-review-graph MCP:

| Task | Tool to use first |
|------|-------------------|
| Find a function or class | `semantic_search_nodes` |
| Understand what calls what | `query_graph` with `callers_of` / `callees_of` |
| Know blast radius of a change | `get_impact_radius` |
| Review changed files | `detect_changes` + `get_review_context` |
| Explore architecture | `get_architecture_overview` + `list_communities` |

Fall back to Grep / Read only when the graph returns no results.

After any edit, run `build_or_update_graph_tool` (incremental) to keep the graph current.

---

## 2. No new files

The scaffold is frozen. Every file that should exist already exists.
Write into existing stubs. Never `touch`, `open(..., 'w')`, or create new `.py` files.

Exceptions: the `tests/` directory may receive new test files if a new module is added,
but new modules require team consensus first (see README team table).

---

## 3. Module ownership — do not touch other contributors' files

| Module / file | Owner | Agent may edit? |
|--------------|-------|-----------------|
| `engine/` | Anas | Yes |
| `preprocessing/video.py` | Anas | Yes |
| `ui/` | Anas | Yes |
| `app.py` | Anas | Yes |
| `preprocessing/image.py` | Sohaila | Only if Anas is blocked |
| `modes/image_in_image.py` | Sohaila | Only if Anas is blocked |
| `modes/image_in_video.py` | Youmna | Only if Anas is blocked |
| `modes/video_in_video.py` | Youstina | Only if Anas is blocked |
| `README.md` | All | Never edit |
| `AGENTS.md` | Anas | Never edit without explicit instruction |

If asked to implement a function in another owner's file, ask for confirmation first.

---

## 4. Style constraints — non-negotiable

- **No Pillow.** Image I/O is `cv2` (opencv-python) only.
- **No subprocess.** Video I/O is `imageio.v3` with `plugin="pyav"` only.
- **PNG only for images.** JPEG destroys LSBs.
- **Lossless video only.** Always `libx264 -crf 0 -preset ultrafast -pix_fmt yuv444p`.
- **Numpy vectorized.** No Python-level loops over pixels or bytes. Use array ops.
- **`@st.cache_data` on every heavy function.** Never add a heavy function to UI without caching.
- **`b` must be 1–4.** Validate and raise `ValueError` at entry of `lsb.embed` / `lsb.decode`.
- **Capacity check before every embed.** Call `engine.capacity.check_capacity` first.
- **XOR on every embed.** Never write plaintext bits. Always `xor_bytes` before `lsb.embed`.
- **Spread spectrum on every embed.** Always call `get_pixel_order` — never sequential LSB.

---

## 5. Function signatures are contracts

The signatures in the stubs (docstrings included) are the spec.
Do not change a signature without also updating `docs/superpowers/specs/2026-04-19-stubs-and-agents-design.md`.

Breaking a signature breaks every caller — use `get_impact_radius` to check before changing.

---

## 6. Commit rules

- One module per commit.
- Message format: `<module>: <verb> <what>` — e.g., `engine/lsb: implement vectorized embed`.
- No `--no-verify`. Hooks run for a reason.

---

## 7. Sidecar metadata schema

Every `modes/*.embed()` returns `(stego_path, meta: dict)`.
The caller writes meta as `<stego_path>.meta.json`. Every `modes/*.decode()` accepts this dict.

Required keys in meta:

```python
{
    "mode": str,           # "image_in_image" | "image_in_video" | "video_in_video"
    "secret_len": int,     # byte length of serialized secret
    "secret_shape": list,  # [H, W, C]
    "secret_dtype": str,   # always "uint8"
    "b": int,              # 1..4
    "fps": float | None,   # video secret only
    "frame_count": int | None,  # video secret only
}
```

Do not add or rename keys without updating all three mode files and the design doc.

---

## 8. What agents must never do

- Mutate `README.md`
- Mutate `AGENTS.md` without explicit user instruction
- Add new top-level Python packages / directories
- Import Pillow (`PIL`) anywhere
- Call `subprocess` or `ffmpeg` CLI directly
- Write sequential LSB (always use spread spectrum)
- Embed without XOR encryption
- Embed without capacity check
