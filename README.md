# Anees

Windows desktop app that downloads YouTube playlists as mono MP3s, with optional speed-up, splitting, and merging.

Powered by the `yt-dlp` Python SDK + `ffmpeg`.

## Stack

- Python 3.12 · PySide6 · yt-dlp SDK · SQLite · PyInstaller
- `ffmpeg` for MP3 conversion, atempo speed-up, and audio splitting

## Setup

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## What it does

1. **Download** — add a YouTube playlist URL; titles + durations fetch immediately; mono MP3 files download on Start run
2. **Speed** — applies an `atempo` ffmpeg filter per playlist (1.0× – 3.0×, pitch-preserved)
3. **Split** — cuts long tracks into N-minute chunks
4. **Merge** — copies all files into one flat folder, optionally with a splitter clip between playlists

## Project layout

```
anees/
  main.py
  ui/
    api/             # UI action layer  (RunAPI, QueueAPI, NavAPI)
    workers/         # QThread wrappers (DownloadWorker, InfoWorker)
    panels/          # queue_list, detail, history, logs
    dialogs/         # add_playlist, merge, diagnostics
    state.py         # AppState — owns PySide6 Signals
    theme.py         # design tokens (colors, spacing, typography)
    widgets.py       # shared primitives (Btn, Badge, Spinner, …)
  backend/
    api/             # public interface for ui/ (DownloadAPI, InfoAPI, stats)
    services/        # internal orchestration (DownloadService, InfoService)
    commands/        # tool wrappers — only place that imports yt_dlp
    utils/           # pure utilities (audio size estimation, …)
    models.py        # Playlist, Video, RunState, … dataclasses
  docs/
    roadmap.md
```

## Status

**Phase 3 complete** — real downloads working end-to-end.

| Feature | Status |
|---------|--------|
| Frameless UI shell — all panels, dialogs, run states | ✅ |
| yt-dlp download + mono MP3 conversion (Phase 3 + 4) | ✅ |
| Playlist info fetch on add (titles + durations) | ✅ |
| Per-video live stage progress (DL → MP3 → Done) | ✅ |
| Estimated size in stats header | ✅ |
| Stop / Pause / Resume | ✅ |
| Speed processing (atempo) | 🔜 Phase 5 |
| Split processing | 🔜 Phase 6 |
| Merge to folder | 🔜 Phase 7 |
| SQLite history | 🔜 Phase 9 |

See [`docs/roadmap.md`](docs/roadmap.md) for the full milestone plan.
