import numpy as np
import soundfile as sf

from get_the_notes.pipeline.chords import SR, detect_chords, fill_gaps, label_chroma
from get_the_notes.pipeline.theory import chord_pitch_classes

PROGRESSION = [(0, ""), (9, "m"), (5, ""), (7, "")]  # C Am F G


def chroma_for(root, quality, noise=0.05, rng=None):
    v = np.full(12, noise)
    for pc in chord_pitch_classes(root, quality):
        v[pc] += 1.0
    if rng is not None:
        v += rng.uniform(0, noise, 12)
    return v


def test_label_chroma_recovers_progression():
    rng = np.random.default_rng(0)
    cols = [chroma_for(r, q, rng=rng) for r, q in PROGRESSION for _ in range(4)]
    labels = label_chroma(np.array(cols).T)
    expected = [c for c in PROGRESSION for _ in range(4)]
    assert labels == expected


def test_label_chroma_smooths_single_beat_glitch():
    # One beat where a passing A makes the C chord look like Am7.
    glitch = chroma_for(0, "")
    glitch[9] += 1.0
    cols = [chroma_for(0, "")] * 4 + [glitch] + [chroma_for(0, "")] * 4
    labels = label_chroma(np.array(cols).T)
    assert set(labels) == {(0, "")}


def synth_chord(pcs, seconds, octave=4):
    t = np.arange(int(seconds * SR)) / SR
    y = np.zeros_like(t)
    for pc in pcs:
        f = 440.0 * 2 ** ((pc + 12 * (octave + 1) - 69) / 12)
        for h, amp in ((1, 1.0), (2, 0.4), (3, 0.2)):
            y += amp * np.sin(2 * np.pi * f * h * t)
    env = np.minimum(1, np.minimum(t, seconds - t) * 20)
    return y * env


def test_detect_chords_on_synthesized_audio(tmp_path):
    y = np.concatenate([synth_chord(chord_pitch_classes(r, q), 2.0) for r, q in PROGRESSION])
    path = tmp_path / "chords.wav"
    sf.write(path, 0.1 * y / np.abs(y).max(), SR)

    analysis = detect_chords(path)
    names = [c.name for c in analysis.chords if c.end - c.start >= 1.0]
    assert names == ["C", "Am", "F", "G"]
    assert analysis.key.name in ("C major", "A minor")


def test_fill_gaps_extends_grid_over_intro_and_outro():
    beats = np.arange(100, 200, 10)
    filled = fill_gaps(beats, 250)
    assert filled[0] == 10 and filled[-1] == 240
    assert set(np.diff(filled)) == {10}
