# Anees — Technical Decisions

## yt-dlp Python SDK instead of CLI

**Decision:** Use `import yt_dlp` (Python SDK), not `yt-dlp.exe` via subprocess.

**Why:**
- Progress and postprocessor hooks are strongly-typed Python callbacks — no output parsing.
- Stop/pause via `threading.Event` checked inside the hook instead of `SIGTERM`.
- No `CREATE_NO_WINDOW` flag needed (no subprocess window to hide).
- ffmpeg bundling in the installer is already required for the SDK path; no second binary needed.

**Constraint:** `import yt_dlp` only in `backend/commands/ytdlp.py`. All callers go through `YtdlpClient`.

---

## CBR 192 kbps mono MP3

**Decision:** `preferredquality: "192"` (CBR) + `-ac 1` (mono downmix).

**Why:**
- VBR `quality: 0` gave ~190 kbps average on test content — CBR 192 is essentially the same quality but predictable file sizes.
- Calibrated against a real 221.8 MB download: 128 kbps estimate was 32% short; 192 kbps is within 1%.
- Mono cuts stereo overhead while preserving all audio content for speech/recitation.

**Size formula:** `duration_sec × 192,000 / 8 / 1,048,576 MB` — exact for CBR.

---

## Pipeline order: DL → MP3 → /Split → ×Speed

**Decision:** Split before speed.

**Why:**
- Applying `atempo` to shorter chunks is faster and produces more consistent output (ffmpeg's atempo is memory-proportional to input length).
- Splitting a sped-up file would also work but loses the "exact chunk length" guarantee.

---

## postprocess_hook: filepath check, not postprocessor name

**Decision:** Trigger split/done logic when `info_dict['filepath'].endswith('.mp3') and os.path.exists(filepath)` rather than `d.get('postprocessor') == 'FFmpegExtractAudio'`.

**Why:**
- yt-dlp's postprocessor key naming has changed between versions (`"FFmpegExtractAudio"` vs `"ffmpegextractaudio"` vs the registered key).
- Checking the filesystem is unambiguous: if the `.mp3` exists, the conversion is done regardless of which postprocessor created it.
- Dedup by filepath in `_done_fps: set[str]` prevents double-processing if multiple postprocessors fire after the MP3 exists.

---

## ffmpeg via subprocess, not a Python binding

**Decision:** `FfmpegClient` in `backend/commands/ffmpeg.py` uses `subprocess.Popen`.

**Why:**
- yt-dlp's `FFmpegExtractAudio` postprocessor handles the download → MP3 conversion internally. We only need ffmpeg directly for *our own* passes (split, speed).
- `subprocess` gives full control: stop via threading.Event, log line-by-line, handle errors via exit code.
- No Python ffmpeg binding adds a dependency without adding value for our use cases.

---

## Separate QFrame for visual separators

**Decision:** Use `QFrame(height=1, background=BORDER)` instead of `border-bottom` on widgets.

**Why:**
- Qt's instance stylesheet applies to a widget **and all its descendants**. Setting `border-right: 1px solid X` on a parent causes every child label to also render a right border.
- A dedicated `QFrame` is a standalone widget with its own stylesheet that doesn't cascade.
- Discovered when the sidebar's `QueueList(border-right)` caused all child QLabels to show right borders.

---

## `ScrollBarAlwaysOff` on video rows

**Decision:** `scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)`.

**Why:**
- When the vertical scrollbar appears it takes 6px of horizontal space, narrowing the viewport relative to `_ColHeader` above it.
- With the scrollbar hidden, viewport width always equals the scroll area width → columns stay aligned.
- Mouse wheel and touchpad scrolling still work without a visible scrollbar.

---

## Disk space check only on button click, not on toolbar refresh

**Decision:** `disk_space_ok()` is called in `_do_start()` only, not in `RunControls.refresh()`.

**Why:**
- `refresh()` is called on every `playlists_changed` signal (potentially many times per second during a run).
- `shutil.disk_usage()` and `Path.mkdir()` are blocking filesystem calls. Running them on every refresh froze the UI — the main thread blocked while waiting for I/O.

---

## Per-playlist subfolder naming

**Decision:** `{output_root}/{prefix}_{safe_playlist_title}/files.mp3`

**Why:**
- Prefix ensures alphabetical sort matches the queue order even when playlist titles are arbitrary.
- Subfolder per playlist keeps the output directory clean and makes partial runs easy to inspect.
- `_safe_name()` replaces non-alphanumeric chars with `_` to avoid path issues on Windows.

---

## Config in `~/.anees/config.json`

**Decision:** Simple JSON, not a database or platform settings API.

**Why:**
- Only a handful of settings (output root, parallel count, default speed).
- Trivially human-readable and editable without the app.
- Cross-platform without extra dependencies.
- Full settings screen (Phase 14) will extend this same file.
