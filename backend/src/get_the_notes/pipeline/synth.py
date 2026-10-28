"""Piano soundtrack for the video: the transcribed notes played back, not the original song.

Uses FluidSynth with a General MIDI soundfont when available (the Docker image ships
both); otherwise falls back to a simple additive piano-like synth so local runs work.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pretty_midi
import soundfile as sf

SAMPLE_RATE = 44100
MELODY_VELOCITY = 100
CHORD_VELOCITY = 62
SOUNDFONTS = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/TimGM6mb.sf2",
    "/usr/share/soundfonts/default.sf2",
]

Note = tuple[float, float, int, int]  # start, end, pitch, velocity


def score_notes(score: dict) -> list[Note]:
    notes = [(n["start"], n["end"], n["pitch"], MELODY_VELOCITY) for n in score["melody"]]
    notes += [
        (c["start"], c["end"], p, CHORD_VELOCITY) for c in score["chords"] for p in c["notes"]
    ]
    return notes


def find_soundfont() -> Path | None:
    candidates = [os.environ.get("GTN_SOUNDFONT", ""), *SOUNDFONTS]
    return next((Path(p) for p in candidates if p and Path(p).is_file()), None)


def synthesize(score: dict, out_path: Path) -> None:
    """Write a mono WAV of the score played on piano, exactly score["duration"] long."""
    notes = score_notes(score)
    n_samples = int(score["duration"] * SAMPLE_RATE)
    fluidsynth, soundfont = shutil.which("fluidsynth"), find_soundfont()
    if fluidsynth and soundfont and notes:
        audio = render_fluidsynth(notes, fluidsynth, soundfont)
    else:
        audio = render_additive(notes, n_samples)

    audio = audio[:n_samples]
    audio = np.pad(audio, (0, n_samples - len(audio)))
    peak = float(np.abs(audio).max())
    if peak > 0:
        audio *= 0.9 / peak
    sf.write(str(out_path), audio.astype(np.float32), SAMPLE_RATE, subtype="PCM_16")


def render_fluidsynth(notes: list[Note], fluidsynth: str, soundfont: Path) -> np.ndarray:
    pm = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Piano")
    piano.notes = [pretty_midi.Note(v, p, s, e) for s, e, p, v in notes]
    pm.instruments.append(piano)
    with tempfile.TemporaryDirectory() as tmp:
        midi, wav = Path(tmp) / "piano.mid", Path(tmp) / "piano.wav"
        pm.write(str(midi))
        cmd = [fluidsynth, "-ni", "-q", "-g", "0.6", "-r", str(SAMPLE_RATE),
               "-F", str(wav), str(soundfont), str(midi)]  # fmt: skip
        subprocess.run(cmd, check=True, capture_output=True)
        audio, _ = sf.read(str(wav), dtype="float32", always_2d=True)
    return audio.mean(axis=1)


def render_additive(notes: list[Note], n_samples: int) -> np.ndarray:
    """A plain decaying-harmonics piano stand-in; good enough to judge pitches by ear."""
    out = np.zeros(n_samples, dtype=np.float64)
    release = 0.12
    for start, end, pitch, velocity in notes:
        i0 = int(start * SAMPLE_RATE)
        dur = max(0.05, end - start)
        length = min(int((dur + release) * SAMPLE_RATE), n_samples - i0)
        if length <= 0:
            continue
        t = np.arange(length) / SAMPLE_RATE
        f = 440.0 * 2 ** ((pitch - 69) / 12)
        decay = 1.2 + f / 500
        tone = sum(
            a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * decay * h)
            for h, a in ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.1))
        )
        env = np.minimum(1.0, t / 0.004) * np.where(t > dur, np.exp(-(t - dur) / 0.04), 1.0)
        out[i0 : i0 + length] += (velocity / 127) * tone * env
    return out
