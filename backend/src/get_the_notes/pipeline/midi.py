from pathlib import Path

import pretty_midi


def write_midi(notes: list[tuple[float, float, int]], path: Path, velocity: int = 80) -> None:
    """Write (start, end, pitch) notes as a single acoustic-piano track."""
    pm = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0, name="Piano")
    for start, end, pitch in notes:
        piano.notes.append(pretty_midi.Note(velocity, int(pitch), float(start), float(end)))
    pm.instruments.append(piano)
    pm.write(str(path))
