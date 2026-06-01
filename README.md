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
    dialogs/         # add_playlist, merge, diagnostics, settings, about
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
    roadmap.md        # milestone/phase plan
    architecture.md   # layer diagram and signal flow
    decisions.md      # why key technical decisions were made
    backend-api.md    # backend API reference for ui/ callers
```

## Status

**Phase 8 complete** — download + split + speed + merge (with optional splitter clip) working end-to-end.

| Feature | Status |
|---------|--------|
| Frameless UI shell — all panels, dialogs, run states | ✅ |
| yt-dlp download + CBR 192 kbps mono MP3 (Phase 3 + 4) | ✅ |
| Playlist info fetch on add (titles + durations) | ✅ |
| Per-video live stage progress (DL → MP3 → Split → Done) | ✅ |
| Split into N-minute chunks via ffmpeg stream copy (Phase 5) | ✅ |
| Configurable output folder + per-playlist subfolders | ✅ |
| Drag-and-drop queue reorder with prefix renumbering | ✅ |
| Estimated size + disk space check before run | ✅ |
| Download console (collapsible terminal panel) | ✅ |
| PyInstaller Windows .exe + macOS .app via GitHub Actions CI | ✅ |
| Speed processing (atempo filter) | ✅ Phase 6 |
| Merge to folder + splitter clip | ✅ Phase 7 + 8 |
| About dialog (branding + Arabic hadith/ayah) | ✅ |
| SQLite history | 🔜 Phase 9 |

See [`docs/roadmap.md`](docs/roadmap.md) for the full milestone plan.

---

## Releasing

Releases are built automatically by GitHub Actions when a version tag is pushed. Both macOS `.app` and Windows `.exe` are produced and attached to the GitHub release.

### Create a release

```bash
# 1. Make sure prod is up to date
git checkout prod
git merge main          # or cherry-pick specific commits

# 2. Tag with a version and push — CI does the rest
git tag v0.2.0 -m "short release notes here"
git push origin prod v0.2.0
```

The `release.yml` workflow triggers, builds both platforms in parallel, and publishes a draft-free release at `github.com/HamzaFouad/anees/releases`.

### Local build (without CI)

```bash
# macOS
./build.sh             # → dist/Anees.app

# Windows
build.bat              # → dist\Anees\Anees.exe
```

### User requirements

The Windows `.exe` bundles ffmpeg — no extra install needed.

macOS `.app` requires ffmpeg separately: `brew install ffmpeg`
