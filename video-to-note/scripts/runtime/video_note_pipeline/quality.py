def duration_delta_ratio(metadata_seconds: float, actual_seconds: float) -> float:
    if metadata_seconds <= 0:
        raise ValueError("metadata_seconds must be greater than 0")
    return abs(actual_seconds - metadata_seconds) / metadata_seconds


def duration_status(metadata_seconds: float, actual_seconds: float, tolerance_percent: float = 5) -> str:
    tolerance = tolerance_percent / 100
    if duration_delta_ratio(metadata_seconds, actual_seconds) <= tolerance:
        return "ok"
    return "abnormal_duration_mismatch"


def transcript_tail_status(
    audio_seconds: float,
    last_segment_end_seconds: float,
    tolerance_percent: float = 5,
) -> str:
    if audio_seconds <= 0:
        raise ValueError("audio_seconds must be greater than 0")
    ratio = abs(audio_seconds - last_segment_end_seconds) / audio_seconds
    if ratio <= tolerance_percent / 100:
        return "transcript_ok"
    return "abnormal_transcript_incomplete"
