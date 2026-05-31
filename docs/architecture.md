# Anees — Architecture

## Layer diagram

```
┌─────────────────────────────────────────────────────┐
│  ui/                                                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  ui/api/    │  │ ui/workers/  │  │ ui/panels │  │
│  │  RunAPI     │  │ DownloadWorker│  │ dialogs   │  │
│  │  QueueAPI   │  │ InfoWorker   │  │ state.py  │  │
│  │  NavAPI     │  └──────┬───────┘  └───────────┘  │
│  └──────┬──────┘         │                          │
└─────────┼────────────────┼──────────────────────────┘
          │                │  (only backend.models and backend.api allowed)
          ▼                ▼
┌─────────────────────────────────────────────────────┐
│  backend/api/      ← public contract                         │
│  DownloadAPI · InfoAPI · SplitAPI · SpeedAPI · stats · config │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  backend/services/  │  ← internal orchestration
          │  DownloadService    │
          │  InfoService        │
          │  SplitService       │
          │  SpeedService       │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  backend/commands/  │  ← tool wrappers
          │  YtdlpClient        │  (only file importing yt_dlp)
          │  FfmpegClient       │  (subprocess to ffmpeg binary)
          └─────────────────────┘
```

## Packages

### `ui/`
PySide6 only. No file I/O, no subprocess, no SQLite.

| Sub-package | Responsibility |
|-------------|----------------|
| `ui/api/` | All state mutations — `RunAPI.start()`, `QueueAPI.add()`, `NavAPI.go()`. Panels never call `state.*` directly except read access. |
| `ui/workers/` | `QThread` subclasses that wrap backend API calls and emit Qt Signals back to the main thread. |
| `ui/panels/` | Display widgets. Read `AppState` properties; call `ui/api/` for mutations. |
| `ui/dialogs/` | Modal dialogs. Same rules as panels. |
| `ui/state.py` | `AppState(QObject)` — owns all PySide6 Signals, throttles UI refreshes, manages `DownloadWorker` lifecycle. |
| `ui/theme.py` | Design tokens: colors, typography, spacing, `PIPELINE_STAGES`. |
| `ui/widgets.py` | Shared primitives: `Btn`, `Badge`, `Toggle`, `Spinner`, `EmptyState`, `Checkbox`, `field()`, `status_dot()`, `icon_button()`. |

## UI styling contract

### Visual ownership

- **Section/container** owns base surface: background, border, radius.
- **Row widget** is transparent by default inside tinted sections.
- **Leaf controls** (labels, checkboxes, buttons) own typography and local interaction visuals.

### Override precedence

1. `ui/theme.py` tokens (color/spacing/radius constants).
2. Shared primitives/helpers in `ui/widgets.py`.
3. Scoped local styles using `setObjectName(...)` + `#id { ... }`.
4. `paintEvent` custom fills only when a widget must intentionally be opaque.

### Guardrails

- Use scoped selectors (`#id`) for container chrome; avoid broad `QWidget { border-* }` rules.
- Prefer dedicated 1px `QFrame` separators over `border-bottom` on layout containers.
- For rows inside tinted containers, keep `background:transparent`, disable autofill/system background, and make selection cues additive (checkbox/accent/text) unless a full row fill is intentional.
- Prefer theme tokens (for example `PRIMARY_TINT_*`, `BORDER`, `ROW_DIVIDER`) over hardcoded rgba/hex values.

### `backend/`
Pure Python. No PySide6 imports anywhere.

| Sub-package | Responsibility |
|-------------|----------------|
| `backend/api/` | Public gateway. `ui/` imports only from here (plus `backend.models`). Each module is a thin facade delegating to services. |
| `backend/services/` | Orchestration. `DownloadService` drives the queue; `SplitService` runs ffmpeg; `InfoService` fetches metadata. Never imported by `ui/`. |
| `backend/commands/` | Tool wrappers. `YtdlpClient` (only file importing `yt_dlp`); `FfmpegClient` (subprocess wrapper). |
| `backend/utils/` | Pure functions: `audio.estimate_size_mb()`, `config.get/set_output_root()`, `config.check_disk_space()`. |
| `backend/models.py` | `@dataclass` definitions: `Playlist`, `Video`, `RunState`, `LogEntry`, …. Shared between `ui/` and `backend/`. |

## Signal flow during a download

```
User clicks Start run
  → ui/api/RunAPI.start()
  → AppState.start_run()
  → DownloadWorker(QThread).start()
       └─ DownloadAPI → DownloadService.execute()
            ├─ InfoService.fetch_playlist()           → videos_ready.emit()
            │       └─ YtdlpClient.fetch_info()
            └─ YtdlpClient.download()  ← yt-dlp thread
                 ├─ on_progress hook   → video_stage.emit()  (download %)
                 └─ on_postprocess hook (fires when MP3 is ready)
                       ├─ video_meta.emit()
                       ├─ if split_enabled:
                       │    video_stage.emit("split")
                       │    executor.submit(_do_split)  ← returns immediately!
                       │    yt-dlp starts next video download ↓
                       └─ else: video_stage.emit("done")

  _do_postprocess() — runs in ThreadPoolExecutor(max_workers=1)
       ├─ SplitService.split_file()     ← concurrent with next video download
       │     └─ FfmpegClient.split()    ← subprocess, killed on stop
       ├─ [if speed != 1.0] video_stage.emit("speed")
       │     └─ SpeedService.apply_speed()
       │           └─ FfmpegClient.speed()  ← atempo re-encode, killed on stop
       └─ video_stage.emit("done")    ← when all post-processing finishes

  ↓ (all signals are queued connections → main thread)
AppState._on_video_stage() → video_row_changed.emit(pid, idx)
                                   ↓
                          DetailPanel._on_video_row_changed()
                                   ↓
                          VideoRow.refresh(video)   ← in-place, no rebuild
```

**Concurrency model:** yt-dlp runs one download at a time (sequential per playlist). Post-processing (split + speed) runs concurrently with the *next* video's download in a single background thread. `executor.shutdown(wait=True)` drains all pending work before `_download()` returns.

## UI refresh throttling

During a run, `_on_video_stage` is called on every progress tick (50–100 times per video). To prevent flooding the main thread:

- **Sidebar** (`playlists_changed`): only emitted when `stage == "done"` (once per video). Throttled via a 300ms `QTimer`.
- **Detail panel** (`video_row_changed`): emitted on every stage *transition* (queued → download → mp3 → done) — direct, no throttle. Updates a single row in-place via `VideoRow.refresh()` without rebuilding the panel.
- **`selection_changed`**: emitted only at structural moments (playlist selected, videos loaded, run complete). Never during a download.
