from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from backend.models import Playlist, Video
from backend.commands.ytdlp import build_info_cmd, build_download_cmd
from backend.commands.runner import CommandRunner

_ITEM_RE = re.compile(r'\[download\] Downloading item (\d+) of (\d+)')
_PROG_RE = re.compile(r'\[download\]\s+([\d.]+)%')
_DONE_RE = re.compile(r'\[download\] 100%')
_AUDIO_RE = re.compile(r'\[ExtractAudio\]|\[Merger\]|\[ffmpeg\]')
_ERR_RE  = re.compile(r'ERROR:')


class DownloadService:
    def __init__(
        self,
        output_root: str | None = None,
        on_videos_ready: Callable[[str, list[Video]], None] | None = None,
        on_video_stage:  Callable[[str, int, str, float], None] | None = None,
        on_log:          Callable[[str, str, str], None] | None = None,
        on_complete:     Callable[[], None] | None = None,
    ):
        self._root = output_root or str(Path.home() / "Downloads" / "Anees")
        self._on_videos_ready = on_videos_ready or (lambda *_: None)
        self._on_video_stage  = on_video_stage  or (lambda *_: None)
        self._on_log          = on_log          or (lambda *_: None)
        self._on_complete     = on_complete     or (lambda: None)
        self._runner  = CommandRunner()
        self._stopped = False

    # ── Public control ────────────────────────────────────────────────────────
    def execute(self, playlists: list[Playlist]) -> None:
        self._stopped = False
        Path(self._root).mkdir(parents=True, exist_ok=True)

        for pl in playlists:
            if self._stopped:
                break
            if pl.status == "done":
                continue
            self._run_playlist(pl)

        if not self._stopped:
            self._on_complete()

    def stop(self)   -> None: self._stopped = True;  self._runner.stop()
    def pause(self)  -> None: self._runner.pause()
    def resume(self) -> None: self._runner.resume()

    # ── Per-playlist logic ────────────────────────────────────────────────────
    def _run_playlist(self, pl: Playlist) -> None:
        # Phase 1: fetch video metadata if the list is empty / placeholder
        if not pl.videos or all(v.title.startswith("Video ") for v in pl.videos):
            videos = self._fetch_info(pl)
            if videos:
                self._on_videos_ready(pl.id, videos)

        if self._stopped:
            return

        # Phase 2: download
        self._download(pl)

    def _fetch_info(self, pl: Playlist) -> list[Video]:
        cmd     = build_info_cmd(pl.url)
        videos: list[Video] = []

        def on_line(line: str) -> None:
            parts = line.split("\t")
            title    = parts[0].strip() if parts else f"Video {len(videos)+1}"
            duration = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else 0
            videos.append(Video(title=title, duration_sec=duration, stage="queued"))

        def on_done(code: int) -> None:
            if code != 0:
                self._on_log("warn", "yt-dlp", f"Info fetch returned code {code} for {pl.url}")

        self._runner.run(cmd, on_line, on_done)
        return videos

    def _download(self, pl: Playlist) -> None:
        cmd = build_download_cmd(pl, self._root)

        current: list[int] = [0]   # 1-based index of video being downloaded
        total:   list[int] = [pl.video_count or 1]

        def on_line(line: str) -> None:
            self._on_log("debug", "yt-dlp", line)

            m = _ITEM_RE.search(line)
            if m:
                # mark previous video done when next item starts
                prev = current[0] - 1
                if prev >= 0:
                    self._on_video_stage(pl.id, prev, "done", 1.0)

                current[0] = int(m.group(1))
                total[0]   = int(m.group(2))
                idx = current[0] - 1
                self._on_video_stage(pl.id, idx, "download", 0.0)
                return

            m = _PROG_RE.search(line)
            if m and current[0] > 0:
                pct = float(m.group(1)) / 100.0
                self._on_video_stage(pl.id, current[0] - 1, "download", pct)
                return

            if _AUDIO_RE.search(line) and current[0] > 0:
                self._on_video_stage(pl.id, current[0] - 1, "mp3", 0.9)
                return

            if _ERR_RE.search(line) and current[0] > 0:
                self._on_log("error", "yt-dlp", line)

        def on_done(code: int) -> None:
            # mark last video done
            if current[0] > 0:
                self._on_video_stage(pl.id, current[0] - 1, "done", 1.0)
            lvl = "info" if code == 0 else "error"
            self._on_log(lvl, "yt-dlp", f"Finished '{pl.title}' (exit {code})")

        self._runner.run(cmd, on_line, on_done)
