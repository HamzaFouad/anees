from __future__ import annotations
import os
import threading
from pathlib import Path

from backend.commands.ytdlp import YtdlpClient


class SplitterService:
    def __init__(self):
        self._client = YtdlpClient()

    def fetch_playlist_videos(self, playlist_url: str) -> list[tuple[str, str, int]]:
        """Return [(webpage_url, title, duration_sec)] for all videos in a playlist."""
        return self._client.fetch_video_urls(playlist_url)

    def fetch_info(self, url: str) -> tuple[str, int]:
        """Return (title, duration_sec) for a single YouTube video URL."""
        videos, title = self._client.fetch_info(url)
        if videos:
            v = videos[0]
            return v.title, v.duration_sec
        return title or url, 0

    def download_clip(
        self,
        url: str,
        dest_folder: str,
        stop: threading.Event | None = None,
    ) -> str:
        """Download *url* as a CBR 192 kbps mono MP3 into *dest_folder*.

        Returns the path of the downloaded file.
        Raises RuntimeError if the download fails or is stopped.
        """
        if stop is None:
            stop = threading.Event()

        Path(dest_folder).mkdir(parents=True, exist_ok=True)
        out_tmpl = os.path.join(dest_folder, "_splitter.%(ext)s")

        downloaded: list[str] = []
        pause = threading.Event()
        pause.set()

        def on_postprocess(d: dict) -> None:
            if d.get("status") != "finished":
                return
            fp = (d.get("info_dict") or {}).get("filepath") or ""
            if fp.lower().endswith(".mp3") and os.path.exists(fp):
                downloaded.append(fp)

        self._client.download(url, out_tmpl, lambda _: None, on_postprocess, stop, pause)

        if stop.is_set():
            raise RuntimeError("Splitter download stopped")
        if not downloaded:
            # fallback: find the file by pattern
            for f in os.listdir(dest_folder):
                if f.startswith("_splitter") and f.endswith(".mp3"):
                    downloaded.append(os.path.join(dest_folder, f))
                    break
        if not downloaded:
            raise RuntimeError("Splitter clip download produced no MP3")
        return downloaded[0]
