from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from backend.types import PlaylistStatus, VideoStage


class RunState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"


@dataclass
class Video:
    title: str
    duration_sec: int
    # Transitional typing: still accepts str while migrating call-sites.
    stage: VideoStage | str
    progress: float = 0.0
    failed_at: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class Playlist:
    id: str
    prefix: str
    title: str
    url: str
    video_count: int
    completed: int
    # Transitional typing: still accepts str while migrating call-sites.
    status: PlaylistStatus | str
    active_stage: VideoStage | str
    speed: float
    split_enabled: bool
    split_min: int
    size_mb: Optional[float]
    added_at: str
    videos: list["Video"] = field(default_factory=list)
    range_start: Optional[int] = None   # 1-based; None = start of playlist
    range_end: Optional[int] = None     # 1-based inclusive; None = end of playlist
    run_state: str = "idle"             # idle | running | paused | done
    source: str = "youtube"             # "youtube" | "local"


@dataclass
class HistoryPlaylist:
    prefix: str
    title: str
    videos: int
    size_mb: float
    speed: float


@dataclass
class HistoryRun:
    id: str
    num: int
    started_at: str
    duration_min: int
    playlist_count: int
    video_count: int
    size_mb: float
    output_path: str
    merged: bool
    merged_path: Optional[str]
    status: str  # success / partial
    playlists: list[HistoryPlaylist] = field(default_factory=list)


@dataclass
class LogEntry:
    t: str
    lvl: str  # error / warn / info / debug
    src: str
    msg: str
    detail: Optional[str] = None
    code: Optional[str] = None
