"""Audio-related utility calculations."""


def estimate_size_mb(total_duration_sec: int, bitrate_kbps: int = 128) -> float:
    """Estimate compressed mono-MP3 file size in MB.

    Formula: duration × bitrate / 8 bits-per-byte / 1,048,576 bytes-per-MB

    The default 128 kbps is a conservative lower bound for mono MP3
    output from yt-dlp with --audio-quality 0 and -ac 1 (mono).
    Actual files are often smaller since most spoken/music content
    compresses well; this keeps the estimate honest.

    Returns 0.0 when no duration data is available.
    """
    if total_duration_sec <= 0:
        return 0.0
    return round(total_duration_sec * bitrate_kbps * 1_000 / 8 / 1_048_576, 1)
