"""Audio-related utility calculations."""

# yt-dlp --audio-quality 0 selects the highest quality YouTube stream
# (typically 192 kbps Opus/AAC), then FFmpeg re-encodes to VBR MP3 at
# quality 0.  With -ac 1 (mono) the average output bitrate is ~190 kbps.
# 192 kbps gives <1% error on calibration against real downloads.
_DEFAULT_BITRATE_KBPS = 192


def estimate_size_mb(total_duration_sec: int, bitrate_kbps: int = _DEFAULT_BITRATE_KBPS) -> float:
    """Estimate mono-MP3 file size in MB.

    Formula: duration × bitrate / 8 bits-per-byte / 1,048,576 bytes-per-MB

    Returns 0.0 when no duration data is available.
    """
    if total_duration_sec <= 0:
        return 0.0
    return round(total_duration_sec * bitrate_kbps * 1_000 / 8 / 1_048_576, 1)
