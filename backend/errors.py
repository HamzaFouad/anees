"""Application-level typed errors."""
from __future__ import annotations


class AneesError(Exception):
    def __init__(
        self,
        *,
        user_message: str,
        code: str,
        technical_message: str | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(technical_message or user_message)
        self.user_message = user_message
        self.code = code
        self.technical_message = technical_message or user_message
        self.recoverable = recoverable


class FfmpegMissingError(AneesError):
    def __init__(self, technical_message: str | None = None) -> None:
        super().__init__(
            user_message="ffmpeg is missing or cannot be executed.",
            code="ANEES-FFMPEG-001",
            technical_message=technical_message,
            recoverable=True,
        )


class DownloadFailedError(AneesError):
    def __init__(self, technical_message: str | None = None) -> None:
        super().__init__(
            user_message="Download failed. Please retry the item.",
            code="ANEES-DL-001",
            technical_message=technical_message,
            recoverable=True,
        )


class InvalidOutputFolderError(AneesError):
    def __init__(self, technical_message: str | None = None) -> None:
        super().__init__(
            user_message="Cannot write to the selected output folder.",
            code="ANEES-FS-001",
            technical_message=technical_message,
            recoverable=True,
        )


class CancelledError(AneesError):
    def __init__(self, technical_message: str | None = None) -> None:
        super().__init__(
            user_message="Operation was cancelled.",
            code="ANEES-RUN-001",
            technical_message=technical_message,
            recoverable=True,
        )
