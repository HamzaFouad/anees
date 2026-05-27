# Anees

Windows desktop app that downloads YouTube playlists as sped-up MP3s, splits long tracks into chunks, and merges playlists into a single folder.

Wraps `yt-dlp` + `ffmpeg` under the hood. The UI shows the exact command that runs before anything touches disk.

## Stack

- Python 3.12 · PySide6 · subprocess · SQLite · PyInstaller
- `yt-dlp` CLI (not the Python API)
- `ffmpeg` for MP3 conversion, atempo speed-up, and audio splitting

## Setup

```bash
# create venv (macOS/Linux)
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

1. **Download** — fetches a YouTube playlist via `yt-dlp`, converts each video to mono MP3
2. **Speed** — applies an `atempo` ffmpeg filter per playlist (1.0× – 3.0×, pitch-preserved)
3. **Split** — cuts long tracks into N-minute chunks
4. **Merge** — copies processed files from all playlists into one flat folder, optionally inserting a short "splitter clip" between each playlist

## Project layout

```
anees/
  main.py              # entry point
  ui/                  # PySide6 only — no file I/O or subprocess here
    main_window.py
    state.py           # AppState with PySide6 Signals
    theme.py
    widgets.py
    titlebar.py
    toolbar.py
    tabs.py
    statusbar.py
    panels/
      queue_list.py
      detail.py
      history.py
      logs.py
    dialogs/
      add_playlist.py
      merge.py
      diagnostics.py
  backend/             # pure Python — no PySide6
    models.py
    mock_data.py
  docs/
    roadmap.md         # full milestone/phase plan
```

## Status

Phase 2 complete — full interactive UI with mock data (no real downloads yet). See [`docs/roadmap.md`](docs/roadmap.md) for the phase plan.
