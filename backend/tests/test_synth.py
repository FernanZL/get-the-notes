import shutil

import numpy as np
import pytest
import soundfile as sf

from get_the_notes.pipeline import synth

SCORE = {
    "duration": 2.0,
    "chords": [{"start": 0.0, "end": 2.0, "notes": [45, 48, 52]}],
    "melody": [{"start": 0.5, "end": 1.0, "pitch": 69}],
}


def test_additive_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    out = tmp_path / "piano.wav"
    synth.synthesize(SCORE, out)
    audio, sr = sf.read(out)
    assert sr == synth.SAMPLE_RATE
    assert len(audio) == 2 * sr
    assert 0.5 < np.abs(audio).max() <= 0.91


def test_additive_pitch_is_correct():
    audio = synth.render_additive([(0.0, 1.0, 69, 100)], synth.SAMPLE_RATE)
    spectrum = np.abs(np.fft.rfft(audio))
    peak_hz = np.argmax(spectrum) * synth.SAMPLE_RATE / len(audio)
    assert abs(peak_hz - 440) < 2


@pytest.mark.skipif(
    not (shutil.which("fluidsynth") and synth.find_soundfont()), reason="no fluidsynth/soundfont"
)
def test_fluidsynth(tmp_path):
    out = tmp_path / "piano.wav"
    synth.synthesize(SCORE, out)
    audio, _ = sf.read(out)
    assert len(audio) == 2 * synth.SAMPLE_RATE and np.abs(audio).max() > 0.5
