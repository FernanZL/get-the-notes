"""Left-hand chord voicings with smooth voice leading."""

LOW, HIGH = 36, 59  # C2..B3
CENTER = 48


def candidates(pitch_classes: list[int]) -> list[list[int]]:
    """Every close-position voicing (each inversion, each octave) that fits in LOW..HIGH."""
    out = []
    n = len(pitch_classes)
    for inv in range(n):
        order = pitch_classes[inv:] + pitch_classes[:inv]
        for base in range(LOW, HIGH + 1):
            if base % 12 != order[0]:
                continue
            notes = [base]
            for pc in order[1:]:
                nxt = notes[-1] + 1
                while nxt % 12 != pc:
                    nxt += 1
                notes.append(nxt)
            if notes[-1] <= HIGH:
                out.append(notes)
    return out


def movement(a: list[int], b: list[int]) -> float:
    """Total distance from each note of a to its nearest note in b (and back)."""
    return sum(min(abs(x - y) for y in b) for x in a) + sum(min(abs(x - y) for y in a) for x in b)


def voice(pitch_classes: list[int], prev: list[int] | None) -> list[int]:
    root = pitch_classes[0]

    def cost(v: list[int]) -> float:
        if prev:
            return (0.0 if v[0] % 12 == root else 3.0) + movement(v, prev)
        # First chord: root position, as close to C3 as possible.
        return (0.0 if v[0] % 12 == root else 12.0) + abs(sum(v) / len(v) - CENTER)

    return min(candidates(pitch_classes), key=cost)


def voice_progression(chords: list[list[int]]) -> list[list[int]]:
    out: list[list[int]] = []
    for pcs in chords:
        out.append(voice(pcs, out[-1] if out else None))
    return out
