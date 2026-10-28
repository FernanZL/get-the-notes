from get_the_notes.pipeline.melody import (
    Note,
    clean_melody,
    drop_short,
    fold_range,
    merge_repeats,
    monophonic,
)


def test_monophonic_keeps_louder_note():
    notes = [Note(0.0, 1.0, 60, 0.3), Note(0.5, 1.5, 64, 0.9)]
    out = monophonic(notes)
    assert [(n.start, n.end, n.pitch) for n in out] == [(0.0, 0.5, 60), (0.5, 1.5, 64)]


def test_monophonic_drops_quieter_overlapping_note():
    notes = [Note(0.0, 1.0, 60, 0.9), Note(0.2, 0.8, 64, 0.2)]
    assert [n.pitch for n in monophonic(notes)] == [60]


def test_drop_short_and_merge_repeats():
    notes = [Note(0.0, 0.5, 62), Note(0.52, 1.0, 62), Note(1.0, 1.03, 70)]
    out = merge_repeats(drop_short(notes))
    assert [(n.start, n.end, n.pitch) for n in out] == [(0.0, 1.0, 62)]


def test_fold_range_preserves_contour_and_range():
    notes = [Note(i, i + 1, p) for i, p in enumerate([48, 50, 52, 53, 55, 24, 100])]
    out = fold_range(notes)
    assert all(60 <= n.pitch <= 84 for n in out)
    assert [n.pitch - out[0].pitch for n in out[:5]] == [0, 2, 4, 5, 7]


def test_clean_melody_empty():
    assert clean_melody([]) == []
