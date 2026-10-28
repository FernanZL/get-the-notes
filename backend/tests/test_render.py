import numpy as np
import soundfile as sf
from imageio_ffmpeg import count_frames_and_secs

from get_the_notes.pipeline.render import Frame, Timeline, background, render_video

SCORE = {
    "title": "Test Song",
    "duration": 3.0,
    "key": "A minor",
    "tempo": 96,
    "chords": [
        {
            "start": 0.0,
            "end": 1.5,
            "name": "Am7",
            "notes": [45, 48, 52, 55],
            "note_names": ["A", "C", "E", "G"],
        },
        {
            "start": 1.5,
            "end": 3.0,
            "name": "Fmaj7",
            "notes": [41, 45, 48, 52],
            "note_names": ["F", "A", "C", "E"],
        },
    ],
    "melody": [
        {"start": 0.2, "end": 0.8, "pitch": 76, "name": "E"},
        {"start": 1.0, "end": 1.4, "pitch": 74, "name": "D"},
        {"start": 1.6, "end": 2.6, "pitch": 70, "name": "Bb"},
    ],
}


def test_timeline_now_and_next():
    line = Timeline([(0.0, 1.0, "C"), (1.0, 2.0, "C"), (2.0, 3.0, "G")])
    assert line.at(0.5) == ("C", "G")
    assert line.at(2.5) == ("G", "–")
    assert line.at(5.0) == ("–", "–")


def test_keyboard_geometry():
    fr = Frame(1920)
    assert len(fr.keys) == 88
    x_c4, w_c4 = fr.keys[60]
    assert w_c4 == 1920 / 52
    assert fr.keys[61][0] < x_c4 + w_c4 < fr.keys[61][0] + fr.keys[61][1]
    assert background(fr, "t", "s").size == (1920, 1080)


def test_render_video(tmp_path):
    audio = tmp_path / "audio.wav"
    sf.write(audio, np.zeros((44100 * 3, 2), dtype="float32"), 44100)
    out = tmp_path / "video.mp4"
    progress = []
    render_video(SCORE, audio, out, width=640, fps=10, on_progress=progress.append)
    frames, secs = count_frames_and_secs(str(out))
    assert frames == 30
    assert abs(secs - 3.0) < 0.2
    assert progress[-1] == 1.0
