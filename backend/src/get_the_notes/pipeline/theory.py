"""Small music-theory helpers: note names, key detection and chord templates."""

from dataclasses import dataclass

import numpy as np

SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Interval sets relative to the root, root first.
CHORD_QUALITIES: dict[str, tuple[int, ...]] = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "dim": (0, 3, 6),
    "sus4": (0, 5, 7),
}

# Krumhansl-Kessler key profiles.
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Tonic pitch classes whose key signature uses flats.
FLAT_MAJOR_TONICS = {5, 10, 3, 8, 1, 6}  # F Bb Eb Ab Db Gb
FLAT_MINOR_TONICS = {2, 7, 0, 5, 10, 3}  # D G C F Bb Eb


@dataclass(frozen=True)
class Key:
    tonic: int
    mode: str  # "major" | "minor"

    @property
    def uses_flats(self) -> bool:
        tonics = FLAT_MAJOR_TONICS if self.mode == "major" else FLAT_MINOR_TONICS
        return self.tonic in tonics

    @property
    def name(self) -> str:
        return f"{pc_name(self.tonic, self.uses_flats)} {self.mode}"


def pc_name(pc: int, flats: bool = False) -> str:
    return (FLAT_NAMES if flats else SHARP_NAMES)[pc % 12]


def note_name(midi: int, flats: bool = False, octave: bool = True) -> str:
    name = pc_name(midi, flats)
    return f"{name}{midi // 12 - 1}" if octave else name


def chord_name(root: int, quality: str, flats: bool = False) -> str:
    return pc_name(root, flats) + quality


def chord_pitch_classes(root: int, quality: str) -> list[int]:
    return [(root + i) % 12 for i in CHORD_QUALITIES[quality]]


def detect_key(chroma_sum: np.ndarray) -> Key:
    """Pick the major/minor key whose profile correlates best with a 12-bin chroma vector."""
    best: tuple[float, Key] | None = None
    for tonic in range(12):
        for mode, profile in (("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)):
            score = float(np.corrcoef(chroma_sum, np.roll(profile, tonic))[0, 1])
            if best is None or score > best[0]:
                best = (score, Key(tonic, mode))
    assert best is not None
    return best[1]
