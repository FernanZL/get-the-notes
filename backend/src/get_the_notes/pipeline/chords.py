"""Chord recognition from the accompaniment stem.

Beat-synchronous chroma is matched against chord templates and smoothed with a
Viterbi pass so labels don't flicker between beats.
"""

from dataclasses import dataclass, field
from pathlib import Path

import librosa
import numpy as np

from .theory import CHORD_QUALITIES, Key, chord_name, chord_pitch_classes, detect_key

SR = 22050
HOP = 512
NO_CHORD = "N"
P_STAY = 0.7
SHARPNESS = 25.0
# Slightly favour plain triads so 7ths are only used when clearly present.
QUALITY_BIAS = {"": 1.0, "m": 1.0, "7": 0.96, "maj7": 0.96, "m7": 0.96, "dim": 0.92, "sus4": 0.93}
SILENCE_RATIO = 0.08


@dataclass
class Chord:
    start: float
    end: float
    root: int | None
    quality: str
    name: str = ""
    notes: list[int] = field(default_factory=list)  # left-hand voicing, filled in later

    @property
    def pitch_classes(self) -> list[int]:
        return [] if self.root is None else chord_pitch_classes(self.root, self.quality)


@dataclass
class ChordAnalysis:
    chords: list[Chord]
    key: Key
    tempo: float


def chord_states() -> list[tuple[int | None, str]]:
    states: list[tuple[int | None, str]] = [(None, NO_CHORD)]
    states += [(root, q) for q in CHORD_QUALITIES for root in range(12)]
    return states


def template_matrix(states: list[tuple[int | None, str]]) -> np.ndarray:
    """(n_states, 12) unit-norm templates; the no-chord row stays zero."""
    t = np.zeros((len(states), 12))
    for i, (root, quality) in enumerate(states):
        if root is None:
            continue
        for pc in chord_pitch_classes(root, quality):
            t[i, pc] = 1.0
        t[i, root] += 0.3
        t[i] /= np.linalg.norm(t[i])
    return t


def label_chroma(chroma: np.ndarray) -> list[tuple[int | None, str]]:
    """Label each column of a (12, n) chroma matrix with a chord state."""
    states = chord_states()
    templates = template_matrix(states)
    energy = chroma.sum(axis=0)
    norm = chroma / (np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-9)

    scores = templates @ norm
    bias = np.array([1.0 if r is None else QUALITY_BIAS[q] for r, q in states])
    scores *= bias[:, None]
    silent = energy < SILENCE_RATIO * (np.median(energy) + 1e-9)
    scores[0] = np.where(silent, 1.0, 0.0)

    prob = np.exp(SHARPNESS * (scores - scores.max(axis=0, keepdims=True)))
    prob /= prob.sum(axis=0, keepdims=True)
    transition = librosa.sequence.transition_loop(len(states), P_STAY)
    path = librosa.sequence.viterbi(prob, transition)
    return [states[i] for i in path]


def beat_frames(y: np.ndarray, duration: float) -> tuple[np.ndarray, float]:
    tempo, beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)
    tempo = float(np.atleast_1d(tempo)[0])
    n_frames = int(librosa.time_to_frames(duration, sr=SR, hop_length=HOP))
    if len(beats) < max(4, duration / 2):
        # Beat tracking failed (e.g. rubato or ambient tracks): use a fixed half-second grid.
        step = librosa.time_to_frames(0.5, sr=SR, hop_length=HOP)
        return np.arange(0, n_frames, step), 0.0
    return fill_gaps(beats, n_frames), tempo


def fill_gaps(beats: np.ndarray, n_frames: int) -> np.ndarray:
    """Extend the beat grid over stretches the tracker skipped (intros, outros, breaks)."""
    period = float(np.median(np.diff(beats)))
    points = np.concatenate([[0], beats, [n_frames]])
    out: list[float] = []
    for a, b in zip(points[:-1], points[1:], strict=True):
        out.append(a)
        if b - a > 1.5 * period:
            out.extend(np.arange(a + period, b - period / 2, period))
    return np.unique(np.round(out).astype(int))[1:]


def detect_chords(accompaniment_path: Path) -> ChordAnalysis:
    y, _ = librosa.load(str(accompaniment_path), sr=SR, mono=True)
    duration = len(y) / SR
    harmonic = librosa.effects.harmonic(y, margin=4)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=SR, hop_length=HOP)

    beats, tempo = beat_frames(y, duration)
    bounds = librosa.util.fix_frames(beats, x_min=0, x_max=chroma.shape[1])
    synced = librosa.util.sync(chroma, bounds, aggregate=np.median)
    times = librosa.frames_to_time(bounds, sr=SR, hop_length=HOP)
    times[-1] = duration

    key = detect_key(chroma.sum(axis=1))
    labels = label_chroma(synced)
    return ChordAnalysis(segments(labels, times, key), key, tempo)


def segments(labels: list[tuple[int | None, str]], times: np.ndarray, key: Key) -> list[Chord]:
    """Merge consecutive equal labels into timed chords, dropping no-chord spans."""
    out: list[Chord] = []
    prev = None
    for i, label in enumerate(labels):
        start, end = float(times[i]), float(times[i + 1])
        if label == prev and out:
            out[-1].end = end
            continue
        prev = label
        root, quality = label
        if root is None:
            continue
        out.append(Chord(start, end, root, quality, chord_name(root, quality, key.uses_flats)))
    return out
