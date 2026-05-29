# backend/api.py
#
# The ONLY backend module that ui/ is allowed to import services from.
# ui/ may also import backend.models (shared data structures).
#
# ui/ must NOT import backend.commands.*, backend.services.*, or
# backend.storage.* directly — use this file instead.

from backend.services.download_service import DownloadService
from backend.services.info_service import InfoService

__all__ = ["DownloadService", "InfoService"]
