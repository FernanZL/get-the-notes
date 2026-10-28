from get_the_notes.pipeline.theory import chord_pitch_classes
from get_the_notes.pipeline.voicing import HIGH, LOW, voice, voice_progression


def test_voicing_in_range_and_complete():
    for root in range(12):
        for quality in ("", "m", "maj7", "7"):
            pcs = chord_pitch_classes(root, quality)
            v = voice(pcs, None)
            assert all(LOW <= p <= HIGH for p in v)
            assert sorted(p % 12 for p in v) == sorted(pcs)


def test_first_chord_has_root_in_bass():
    v = voice(chord_pitch_classes(0, ""), None)
    assert v[0] % 12 == 0


def test_progression_moves_smoothly():
    progression = [chord_pitch_classes(r, q) for r, q in [(0, ""), (9, "m"), (5, ""), (7, "")]]
    voicings = voice_progression(progression)
    for a, b in zip(voicings, voicings[1:], strict=False):
        assert abs(sum(a) / len(a) - sum(b) / len(b)) <= 6
