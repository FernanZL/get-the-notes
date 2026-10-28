import shutil
import subprocess
from functools import cache
from pathlib import Path

import soundfile as sf


class PipelineError(Exception):
    """An error whose message is safe to show to the user."""


@cache
def ffmpeg_exe() -> str:
    system = shutil.which("ffmpeg")
    if system:
        return system
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def decode(src: Path, dst: Path, sample_rate: int = 44100) -> float:
    """Decode any audio file to stereo 16-bit WAV. Returns the duration in seconds."""
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "2",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dst.exists():
        raise PipelineError("Could not read this file as audio.")
    duration = sf.info(str(dst)).duration
    if duration < 1:
        raise PipelineError("The audio is too short.")
    return duration
