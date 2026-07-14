def render_quality_report(
    video_id: str,
    metadata_duration: float | None,
    audio_duration: float | None,
    duration_check_status: str,
    last_segment_end: float | None,
    transcript_check_status: str,
    abnormal_notes: list[str],
    commands: list[str] | None = None,
) -> str:
    command_lines = commands or []
    note_lines = abnormal_notes or []

    lines = [
        f"# Quality Report: {video_id}",
        "",
        "## Duration",
        f"- metadata_duration: {metadata_duration}",
        f"- audio_duration: {audio_duration}",
        f"- duration_status: {duration_check_status}",
        "",
        "## Transcript",
        f"- last_segment_end: {last_segment_end}",
        f"- transcript_status: {transcript_check_status}",
        "",
        "## Commands",
    ]
    if command_lines:
        lines.extend(f"- `{command}`" for command in command_lines)
    else:
        lines.append("- No commands recorded yet.")

    lines.extend(["", "## Abnormal Notes"])
    if note_lines:
        lines.extend(f"- {note}" for note in note_lines)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"
