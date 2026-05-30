# Anees — Backend API Reference

`ui/` imports services **only** from `backend/api/`. This page documents every public export.

## `backend.api`

```python
from backend.api import (
    DownloadAPI, InfoAPI, SplitAPI,
    playlist_size_estimate, playlist_total_duration,
    get_output_root, set_output_root,
)
```

---

### `DownloadAPI`

Drives a full download run.

```python
api = DownloadAPI(
    output_root     = "/path/to/output",   # optional, default from config
    on_videos_ready = callable,             # (pid, list[Video], title)
    on_video_stage  = callable,             # (pid, idx, stage, progress)
    on_video_meta   = callable,             # (pid, idx, title, duration_sec)
    on_log          = callable,             # (level, src, msg)
    on_complete     = callable,             # ()
)
api.execute(playlists)
api.stop()
api.pause()
api.resume()
```

Stage values: `"queued"` → `"download"` → `"mp3"` → `"split"` (if enabled) → `"done"` / `"failed"`

---

### `InfoAPI`

Fetches playlist metadata without downloading.

```python
videos, title = InfoAPI().fetch_playlist(url)
# Returns (list[Video], playlist_title_str)
# Videos have: title, duration_sec, stage="queued"
# Uses extract_flat=True — fast (1 request); Shorts may return duration=0
```

---

### `SplitAPI`

Splits a single MP3 file into N-minute chunks.

```python
parts = SplitAPI().split_file(
    input_path  = "/path/to/file.mp3",
    chunk_min   = 30,
    on_log      = callable,             # optional
    stop        = threading.Event(),    # optional
)
# Returns list[str] of output file paths
# Deletes input_path on success
# Returns [input_path] on failure
```

---

### Stats

```python
est_mb   = playlist_size_estimate(playlist)   # float — CBR 192kbps estimate
total_s  = playlist_total_duration(playlist)  # int — sum of video durations
```

---

### Config

```python
root = get_output_root()        # str — reads ~/.anees/config.json, default ~/Downloads/Anees
set_output_root("/new/path")    # persists to config
```

---

## Adding a new backend capability

1. Implement in `backend/services/your_service.py`
2. Create `backend/api/your_module.py` as a thin facade
3. Export from `backend/api/__init__.py`
4. Update this file

Never expose `backend/services/` or `backend/commands/` directly to `ui/`.
