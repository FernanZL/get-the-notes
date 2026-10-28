import numpy as np

from get_the_notes.pipeline.theory import (
    MAJOR_PROFILE,
    MINOR_PROFILE,
    Key,
    chord_name,
    detect_key,
    note_name,
)


def test_note_names():
    assert note_name(60) == "C4"
    assert note_name(70, flats=True) == "Bb4"
    assert note_name(70) == "A#4"
    assert note_name(69, octave=False) == "A"


def test_key_spelling():
    assert Key(5, "major").uses_flats  # F major
    assert not Key(7, "major").uses_flats  # G major
    assert Key(2, "minor").name == "D minor"
    assert chord_name(10, "maj7", flats=True) == "Bbmaj7"


def test_detect_key_from_profiles():
    assert detect_key(np.roll(MAJOR_PROFILE, 7)) == Key(7, "major")
    assert detect_key(np.roll(MINOR_PROFILE, 9)) == Key(9, "minor")
