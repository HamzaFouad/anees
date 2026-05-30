# Anees — Development Roadmap

**Anees** is a Windows 10/11 desktop app that wraps `yt-dlp` + `ffmpeg` to download YouTube playlists as sped-up MP3s, optionally split long tracks, then merge everything into a single flat folder with audible playlist separators.

**Stack:** Python · PySide6 · subprocess · SQLite · PyInstaller  
**Design:** Variation B v2 — two-pane compact, 1100×720 frameless window (see `/tmp/anees_design/` for the exported Claude Design handoff bundle)

Each phase is independently shippable and delivers end-to-end value before the next phase begins.

---

## Milestone 1 — Download & Convert *(Core)*

> Goal: User adds a YouTube playlist URL and gets MP3 files in an output folder.

---

### Phase 1 · Docs ✅

**Shippable as:** Living project reference.

- Create `docs/roadmap.md` with full milestone/phase plan.

---

### Phase 2 · UI Shell (mock data, no backend) ✅

**Shippable as:** Interactive design prototype — validates the UI and all workflows before any backend work.

| File | Purpose |
|------|---------|
| `requirements.txt` | PySide6>=6.7, requests |
| `main.py` | QApplication entry point, font loading, launch window |
| `ui/theme.py` | Color constants, global QSS, Inter/JetBrains Mono font loading |
| `ui/widgets.py` | Shared primitives: Btn, Badge, Toggle, ProgressBar, PipelineStrip, StyledInput, Field |
| `ui/titlebar.py` | Frameless Windows titlebar — drag, min/max/close |
| `ui/toolbar.py` | Top bar: logo, RunControls (idle/running/paused/complete), Add, Search, Settings |
| `ui/tabs.py` | Queue / History / Logs tab bar with counts + "locked" pill |
| `ui/statusbar.py` | yt-dlp version · ffmpeg · parallel count · disk free |
| `ui/panels/queue_list.py` | Left pane: playlist items, empty state, Add button |
| `ui/panels/detail.py` | Right pane: playlist header + video rows (DL / MP3 / × / / stage cells) |
| `ui/panels/history.py` | History tab with expandable run rows (mock data) |
| `ui/panels/logs.py` | Logs tab: level filters, expandable stack traces (mock data) |
| `ui/dialogs/add_playlist.py` | URL · prefix · speed toggle · split toggle · live yt-dlp command preview |
| `ui/dialogs/merge.py` | Playlist checklist + splitter clip toggle with mock Fetch |
| `ui/dialogs/diagnostics.py` | Bundle checklist · send → success confirmation |
| `ui/state.py` | `AppState`: run_state, playlists, selected_id, view — PySide6 Signals |
| `ui/main_window.py` | Assembles all panels, owns AppState, wires all signals |
| `backend/models.py` | `@dataclass` Playlist, Video, HistoryRun, LogEntry; `RunState` enum |
| `backend/mock_data.py` | MOCK_PLAYLISTS, SAMPLE_VIDEOS, MOCK_HISTORY, MOCK_LOGS |

All state transitions work with mock data:

| Scenario | What's interactive |
|----------|-------------------|
| Empty queue | Empty state, Add CTA is primary |
| Idle w/ items | Start run enabled, Add/remove playlists, drag to reorder hint |
| Running | Queue locked, Pause/Stop, pulsing dot, locked pill in tabs |
| Paused | Resume/Stop, amber status text |
| Complete | Merge to folder + New run |
| History tab | Expandable run rows, re-run back to queue view |
| Logs tab | Level filter pills, errors pre-expanded, Send Diagnostics |
| Add dialog | URL updates yt-dlp command preview live |
| Merge dialog | Playlist checklist, splitter toggle + mock Fetch, order preview |
| Diagnostics | Bundle checklist, send → success + reference code |
| Retry | Per-video and "Retry N failed" optimistically resets stage |

**Run:** `pip install -r requirements.txt && python main.py`

---

### Phase 3 · yt-dlp Download Integration ✅

**Shippable as:** User can download a real YouTube playlist to disk.

| File | Purpose |
|------|---------|
| `backend/commands/ytdlp.py` | `build_download_cmd(playlist, output_root) → list[str]` |
| `backend/commands/runner.py` | `CommandRunner`: `subprocess.Popen(CREATE_NO_WINDOW)`, emits log lines via Signal |
| `backend/services/download_service.py` | `DownloadService` in QThread: drives queue, parses `[N/M]` progress, updates Video.stage |

- Start run → real yt-dlp subprocess
- Progress feeds back to queue list + detail panel in real time
- Failed videos get `stage=failed` with error message from stderr
- Stop / Pause / Resume interrupts or pauses the subprocess

---

### Phase 4 · ffmpeg MP3 Conversion ✅

**Shippable as:** Downloaded audio is transcoded to mono MP3.

> **Subsumed into Phase 3.** The original plan assumed a separate ffmpeg subprocess after each yt-dlp download. Switching to the yt-dlp Python SDK made this unnecessary — `FFmpegExtractAudio` runs as a built-in postprocessor inside `YtdlpClient.download()`, producing CBR 192 kbps mono MP3 in a single pass.
>
> What is already implemented in `backend/commands/ytdlp.py`:
> - `FFmpegExtractAudio` postprocessor with `preferredcodec: "mp3"` and `preferredquality: "192"`
> - `-ac 1` postprocessor arg for mono downmix
> - `Video.stage` advances `download → mp3 → done` via `on_progress` and `postprocessor_hooks`
> - Pipeline strip shows **DL → MP3 → Done** correctly

---

## Milestone 2 — Audio Splitting

> Goal: Long tracks (> N minutes) are split into N-minute chunks.

---

### Phase 5 · Split Processing ✅

| File | Purpose |
|------|---------|
| `backend/commands/ffmpeg.py` | `build_split_cmd(input, output_dir, chunk_min) → list[str]` (uses `-f segment -segment_time`) |
| `backend/services/split_service.py` | Runs split pass after MP3; advances stage: mp3 → split |

- Split toggle + chunk length set per-playlist in Add Playlist dialog
- Output naming: `00_01_Title_part01.mp3`, `00_01_Title_part02.mp3`, …
- Split before speed so the atempo filter runs on shorter files (faster)

Pipeline: **DL → MP3 → /Split**

---

## Milestone 3 — Speed Control

> Goal: Each playlist has a configurable playback speed multiplier; processed files play back faster.

---

### Phase 6 · Speed Processing

| File | Purpose |
|------|---------|
| `backend/commands/ffmpeg.py` | `build_atempo_filter(speed: float) → str` — chains filters when speed > 2.0 |
| `backend/services/speed_service.py` | Runs atempo pass after split; advances stage: split → speed |

- Speed value set per-playlist in Add Playlist dialog
- Default speed from Settings (Phase 13)
- For speed > 2.0: chains `atempo` filters (`atempo=sqrt(N),atempo=sqrt(N)`)

Pipeline: **DL → MP3 → /Split → ×Speed**

---

## Milestone 4 — Merge to Folder

> Goal: All processed playlists are copied into one flat folder, optionally with an audio splitter clip inserted between each playlist.

---

### Phase 7 · Merge Functionality

| File | Purpose |
|------|---------|
| `backend/services/merge_service.py` | Copies MP3s from selected playlist folders into destination in prefix order |

- Merge dialog wired to real file copy (with progress feedback)

---

### Phase 8 · Splitter Clip

| File | Purpose |
|------|---------|
| `backend/services/splitter_service.py` | Downloads a single YouTube URL via yt-dlp, inserts `_splitter_*.mp3` between each playlist in merged output |

- Merge dialog "Fetch" button calls real yt-dlp, shows resolved video card
- Output order: `playlist_A_files… → _splitter.mp3 → playlist_B_files… → _splitter.mp3 → …`

---

## Milestone 5 — History & Re-run

> Goal: Every completed run is logged to disk; user can browse past runs and repeat them.

---

### Phase 9 · SQLite Storage

| File | Purpose |
|------|---------|
| `backend/storage/db.py` | `init_db()`, schema: `runs`, `run_playlists` |
| `backend/storage/history_repo.py` | `save_run(run)`, `list_runs()`, `get_run(id)` |

- On run complete → auto-save to `~/.anees/history.db`

---

### Phase 10 · History Tab (real data)

- History tab reads from `history_repo.list_runs()` instead of mock data
- Re-run: load playlists from saved run → populate queue → switch to idle queue view

---

## Milestone 6 — Logs & Diagnostics

> Goal: All subprocess output is surfaced in the Logs tab; user can send a diagnostic bundle to the developer.

---

### Phase 11 · Live Log Streaming

| File | Purpose |
|------|---------|
| `backend/services/log_service.py` | Collects all subprocess lines with timestamp + inferred severity level |

- `LogEntry` objects stored in `AppState.logs`
- Logs tab reads live from state (level filters, auto-scroll, expandable stack traces all wire to real data)

---

### Phase 11.5 · Download Console ✅

**Shippable as:** Users can see exactly what yt-dlp and ffmpeg are doing in real time — like Postman's Console panel, toggleable without leaving the download view.

| File | Purpose |
|------|---------|
| `ui/panels/console.py` | Collapsible dark terminal panel embedded below the video rows in the detail panel |

- Toggle button (▶ Console) in the detail panel header shows/hides the panel
- Streams raw yt-dlp and ffmpeg output lines with timestamps and colour-coded severity (INFO · WARN · ERROR)
- Auto-scrolls during active downloads; can be paused and cleared
- Lines are sourced from `AppState.logs` filtered to the selected playlist
- Closed by default; state persists per session

---

### Phase 12 · Send Diagnostics

| File | Purpose |
|------|---------|
| `backend/services/diagnostics_service.py` | Bundles: anonymized logs, system info, tool versions, config, queue state |

- Strips usernames / file paths / YouTube URLs before sending
- Sends HTTP POST to developer endpoint (configurable; v1 can copy to clipboard)
- Reference code generated locally (`ANEES-YYYY-MM-DD-#XXXX`)

---

## Milestone 7 — Polish & Packaging

> Goal: App is production-ready and installable on a fresh Windows machine.

---

### Phase 13 · Retry Failed Videos

- Download / speed / split services support re-running a single video by index
- `DownloadService.retry(playlist_id, video_idx)` — resets stage, increments retry count
- "Retry N failed" retries all failed videos in a playlist at once

---

### Phase 14 · Settings Screen

| File | Purpose |
|------|---------|
| `ui/dialogs/settings.py` | Paths to yt-dlp.exe / ffmpeg.exe / ffprobe.exe, output root, default speed, mono toggle, parallel downloads |
| `backend/storage/config_repo.py` | Read/write `~/.anees/config.json` |

---

### Phase 15 · PyInstaller Packaging ✅

| File | Purpose |
|------|---------|
| `anees.spec` | Bundles app + `vendor/win-x64/{yt-dlp.exe,ffmpeg.exe,ffprobe.exe}` |
| `build.bat` | `pyinstaller anees.spec` |

Output: `dist/Anees/Anees.exe` (one-folder mode)

---

### Phase 16 · Windows Installer

| File | Purpose |
|------|---------|
| `installer/anees.iss` | Inno Setup script |

- Installs to `%LocalAppData%\Anees`
- Creates Start Menu + Desktop shortcuts
- Output: `dist/AneesSetup.exe`

---

## Final project structure

```
anees/
  CLAUDE.md                        ← architecture rules for Claude
  requirements.txt
  main.py                          ← entry point: wires ui ↔ backend
  docs/
    roadmap.md                     ← this file
  ui/                              ← PySide6 only; may import from backend/
    main_window.py
    state.py                       ← AppState (owns PySide6 Signals)
    theme.py
    widgets.py                     ← Btn, Badge, Toggle, ProgressBar, PipelineStrip, …
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
      settings.py
  backend/                         ← pure Python; never imports from ui/
    models.py                      ← Playlist, Video, HistoryRun, LogEntry dataclasses
    mock_data.py
    commands/
      ytdlp.py
      ffmpeg.py
      runner.py                    ← subprocess.Popen, streams lines via callback
    services/
      download_service.py
      mp3_service.py
      speed_service.py
      split_service.py
      merge_service.py
      splitter_service.py
      log_service.py
      diagnostics_service.py
    storage/
      db.py
      history_repo.py
      config_repo.py
  vendor/
    win-x64/
      yt-dlp.exe
      ffmpeg.exe
      ffprobe.exe
  anees.spec
  installer/
    anees.iss
```
