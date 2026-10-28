"""Vocal melody transcription: basic-pitch, then reduced to a clean single line."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

MIN_NOTE_S = 0.08
MERGE_GAP_S = 0.05
LOW, HIGH = 60, 84  # C4..C6, the right-hand range
CENTER = 72


@dataclass
class Note:
    start: float
    end: float
    pitch: int
    amplitude: float = 1.0

    @property
    def duration(self) -> float:
        return self.end - self.start


def transcribe(vocals_path: Path) -> list[Note]:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    _, _, events = predict(
        str(vocals_path),
        ICASSP_2022_MODEL_PATH,
        onset_threshold=0.5,
        frame_threshold=0.3,
        minimum_note_length=MIN_NOTE_S * 1000,
        minimum_frequency=70.0,
        maximum_frequency=1400.0,
        melodia_trick=True,
    )
    notes = [Note(float(s), float(e), int(p), float(a)) for s, e, p, a, _ in events]
    return clean_melody(notes)


def clean_melody(notes: list[Note]) -> list[Note]:
    return fold_range(merge_repeats(drop_short(monophonic(notes))))


def monophonic(notes: list[Note]) -> list[Note]:
    """Resolve overlaps so only one note sounds at a time, preferring the louder one."""
    out: list[Note] = []
    for n in sorted(notes, key=lambda n: (n.start, -n.amplitude)):
        n = Note(n.start, n.end, n.pitch, n.amplitude)
        if out and n.start < out[-1].end:
            prev = out[-1]
            if n.amplitude > prev.amplitude:
                prev.end = n.start
                if prev.duration < MIN_NOTE_S:
                    out.pop()
            elif n.end > prev.end:
                n.start = prev.end
            else:
                continue
        if n.duration > 0:
            out.append(n)
    return out


def drop_short(notes: list[Note]) -> list[Note]:
    return [n for n in notes if n.duration >= MIN_NOTE_S]


def merge_repeats(notes: list[Note]) -> list[Note]:
    out: list[Note] = []
    for n in notes:
        if out and out[-1].pitch == n.pitch and n.start - out[-1].end < MERGE_GAP_S:
            out[-1].end = max(out[-1].end, n.end)
            out[-1].amplitude = max(out[-1].amplitude, n.amplitude)
        else:
            out.append(Note(n.start, n.end, n.pitch, n.amplitude))
    return out


def fold_range(notes: list[Note]) -> list[Note]:
    """Shift the line by whole octaves to sit around C5, then fold stragglers into C4..C6."""
    if not notes:
        return []
    median = float(np.median([n.pitch for n in notes]))
    shift = 12 * round((CENTER - median) / 12)
    out = []
    for n in notes:
        p = n.pitch + shift
        while p < LOW:
            p += 12
        while p > HIGH:
            p -= 12
        out.append(Note(n.start, n.end, p, n.amplitude))
    return out
