"""Audio-related utility calculations."""

# Output is CBR 192 kbps mono MP3 (preferredquality="192", -ac 1).
# For CBR the calculation is exact: size = duration × bitrate / 8.
# If the source stream is below 192 kbps, ffmpeg encodes at the source
# bitrate instead — the actual file will be smaller in that case.
_DEFAULT_BITRATE_KBPS = 192


def estimate_size_mb(total_duration_sec: int, bitrate_kbps: int = _DEFAULT_BITRATE_KBPS) -> float:
    """Calculate expected mono-MP3 file size in MB for CBR output.

    Formula: duration × bitrate / 8 bits-per-byte / 1,048,576 bytes-per-MB

    Returns 0.0 when no duration data is available.
    """
    if total_duration_sec <= 0:
        return 0.0
    return round(total_duration_sec * bitrate_kbps * 1_000 / 8 / 1_048_576, 1)
