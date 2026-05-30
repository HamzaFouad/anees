"""backend.api — public contract between ui/ and backend/.

ui/ imports ONLY from here (plus backend.models).
Never import backend.services.*, backend.commands.*, or backend.storage.* from ui/.
"""

from backend.api.download import DownloadAPI
from backend.api.info import InfoAPI
from backend.api.stats import playlist_size_estimate, playlist_total_duration

__all__ = ["DownloadAPI", "InfoAPI", "playlist_size_estimate", "playlist_total_duration"]
