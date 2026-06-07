"""backend.api — public contract between ui/ and backend/.

ui/ imports ONLY from here (plus backend.models).
Never import backend.services.*, backend.commands.*, or backend.storage.* from ui/.
"""

from backend.api.download import DownloadAPI
from backend.api.info import InfoAPI
from backend.api.split import SplitAPI
from backend.api.speed import SpeedAPI
from backend.api.merge import MergeAPI
from backend.api.stats import playlist_size_estimate, playlist_total_duration
from backend.api.config import get_output_root, set_output_root
from backend.api.health import ffmpeg_ok, get_ffmpeg_version, get_ytdlp_version

__all__ = [
    "DownloadAPI", "InfoAPI", "SplitAPI", "SpeedAPI", "MergeAPI",
    "playlist_size_estimate", "playlist_total_duration",
    "get_output_root", "set_output_root",
    "ffmpeg_ok", "get_ffmpeg_version", "get_ytdlp_version",
]
