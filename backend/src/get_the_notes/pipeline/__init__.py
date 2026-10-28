"""End-to-end processing: song file in, tutorial video + MIDI + notes.json out."""

import json
from collections.abc import Callable
from pathlib import Path

from .audio import PipelineError, decode

__all__ = ["STAGES", "PipelineError", "overall_progress", "run_pipeline"]

# Stage name -> share of the overall progress bar.
STAGES = {
    "decoding": 0.02,
    "separating": 0.43,
    "melody": 0.12,
    "chords": 0.08,
    "rendering": 0.35,
}

Reporter = Callable[[str, float], None]


def overall_progress(stage: str, fraction: float) -> float:
    done = 0.0
    for name, weight in STAGES.items():
        if name == stage:
            return done + weight * max(0.0, min(1.0, fraction))
        done += weight
    return 1.0 if stage == "done" else 0.0


def run_pipeline(
    job_dir: Path,
    input_path: Path,
    title: str,
    report: Reporter = lambda stage, fraction: None,
    max_duration_s: float | None = None,
) -> dict:
    from . import chords as chords_mod
    from . import melody, render, separate, synth
    from .midi import write_midi
    from .theory import note_name
    from .voicing import voice_progression

    report("decoding", 0.0)
    wav = job_dir / "audio.wav"
    duration = decode(input_path, wav)
    if max_duration_s and duration > max_duration_s:
        raise PipelineError(f"Songs can be at most {int(max_duration_s // 60)} minutes long.")

    report("separating", 0.0)
    vocals, accompaniment = separate.separate(
        wav, job_dir / "stems", on_progress=lambda f: report("separating", f)
    )

    report("melody", 0.0)
    tune = melody.transcribe(vocals)

    report("chords", 0.0)
    analysis = chords_mod.detect_chords(accompaniment)
    flats = analysis.key.uses_flats
    for chord, notes in zip(
        analysis.chords,
        voice_progression([c.pitch_classes for c in analysis.chords]),
        strict=True,
    ):
        chord.notes = notes

    score = {
        "title": title,
        "duration": duration,
        "key": analysis.key.name,
        "tempo": round(analysis.tempo, 1),
        "chords": [
            {
                "start": round(c.start, 3),
                "end": round(c.end, 3),
                "name": c.name,
                "notes": c.notes,
                "note_names": [note_name(p, flats, octave=False) for p in c.notes],
            }
            for c in analysis.chords
        ],
        "melody": [
            {
                "start": round(n.start, 3),
                "end": round(n.end, 3),
                "pitch": n.pitch,
                "name": note_name(n.pitch, flats, octave=False),
            }
            for n in tune
        ],
    }
    (job_dir / "notes.json").write_text(json.dumps(score, indent=1))
    write_midi(
        [(n["start"], n["end"], n["pitch"]) for n in score["melody"]], job_dir / "melody.mid"
    )
    write_midi(
        [(c["start"], c["end"], p) for c in score["chords"] for p in c["notes"]],
        job_dir / "chords.mid",
        velocity=64,
    )

    # The video's soundtrack is the transcription played on piano, so you can hear
    # whether the notes are right instead of hearing the original recording.
    report("rendering", 0.0)
    piano = job_dir / "piano.wav"
    synth.synthesize(score, piano)
    render.render_video(
        score, piano, job_dir / "video.mp4", on_progress=lambda f: report("rendering", f)
    )
    report("done", 1.0)
    return score
