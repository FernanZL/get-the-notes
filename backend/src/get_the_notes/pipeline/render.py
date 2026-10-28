"""Falling-notes piano video renderer.

Layout and colours follow the "Rendered video frame" artboard of the design:
a 1920x1080 frame, 860 px of falling-note area above an 88-key keyboard,
teal for left-hand chords and amber for the right-hand vocal melody.
Frames are drawn with Pillow and piped as raw RGB into ffmpeg.
"""

import subprocess
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audio import PipelineError, ffmpeg_exe

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

BASE_W, BASE_H = 1920, 1080
FALL_H, KB_H, BLACK_H = 860, 220, 136
LOOKAHEAD_S = 3.2
LOWEST, HIGHEST = 21, 108  # A0..C8

BG = (7, 8, 10)
LANE = (20, 23, 28)
HIT_LINE = (58, 64, 75)
WHITE_KEY = (232, 234, 237)
BLACK_KEY = (21, 24, 29)
KEY_LABEL = (91, 98, 112)
TEXT = (232, 234, 237)
MUTED = (154, 161, 172)
TRACK = (30, 34, 41)
TEAL, TEAL_DARK, TEAL_TEXT, TEAL_TAG = (31, 181, 163), (23, 138, 125), (46, 196, 176), (15, 42, 39)
AMBER, AMBER_DARK = (255, 181, 71), (217, 144, 42)
HAND_COLORS = {"L": (TEAL, TEAL_DARK), "R": (AMBER, AMBER_DARK)}


def is_black(midi: int) -> bool:
    return midi % 12 in (1, 3, 6, 8, 10)


@dataclass
class Bar:
    start: float
    end: float
    pitch: int
    hand: str  # "L" | "R"
    label: str


@cache
def font(name: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size)
    axes = f.get_variation_axes()
    values = []
    for axis in axes:
        axis_name = axis["name"].decode() if isinstance(axis["name"], bytes) else axis["name"]
        values.append(weight if axis_name.lower() == "weight" else axis["default"])
    f.set_variation_by_axes(values)
    return f


def sans(size: float, weight: int = 400) -> ImageFont.FreeTypeFont:
    return font("InstrumentSans.ttf", max(1, round(size)), weight)


def mono(size: float, weight: int = 500) -> ImageFont.FreeTypeFont:
    return font("JetBrainsMono.ttf", max(1, round(size)), weight)


class Frame:
    """Geometry for one output resolution; every base-layout number is scaled by `s`."""

    def __init__(self, width: int):
        self.s = s = width / BASE_W
        self.w, self.h = width, round(BASE_H * s)
        self.w -= self.w % 2
        self.h -= self.h % 2
        self.fall_h = FALL_H * s
        self.pps = self.fall_h / LOOKAHEAD_S
        ww = self.w / 52
        bw = ww * 0.6
        self.keys: dict[int, tuple[float, float]] = {}
        wi = 0
        for m in range(LOWEST, HIGHEST + 1):
            if is_black(m):
                self.keys[m] = (wi * ww - bw / 2, bw)
            else:
                self.keys[m] = (wi * ww, ww)
                wi += 1

    def white_key(self, d: ImageDraw.ImageDraw, m: int, fill) -> None:
        x, w = self.keys[m]
        s = self.s
        d.rounded_rectangle(
            (x, self.fall_h, x + w - 2 * s, self.fall_h + KB_H * s),
            radius=6 * s,
            fill=fill,
            corners=(False, False, True, True),
        )

    def black_key(self, d: ImageDraw.ImageDraw, m: int, fill) -> None:
        x, w = self.keys[m]
        s = self.s
        d.rounded_rectangle(
            (x, self.fall_h, x + w, self.fall_h + BLACK_H * s),
            radius=4 * s,
            fill=fill,
            corners=(False, False, True, True),
        )


def background(fr: Frame, title: str, subtitle: str) -> Image.Image:
    s = fr.s
    img = Image.new("RGB", (fr.w, fr.h), BG)
    d = ImageDraw.Draw(img)
    for m in range(24, HIGHEST + 1, 12):
        x = fr.keys[m][0]
        d.rectangle((x, 0, x + max(1, s), fr.fall_h), fill=LANE)
    d.rectangle((0, fr.fall_h - 4 * s, fr.w, fr.fall_h), fill=HIT_LINE)
    for m in range(LOWEST, HIGHEST + 1):
        if not is_black(m):
            fr.white_key(d, m, WHITE_KEY)
            if m % 12 == 0:
                x, w = fr.keys[m]
                d.text(
                    (x + w / 2, fr.fall_h + (KB_H - 10) * s),
                    f"C{m // 12 - 1}",
                    font=mono(13 * s),
                    fill=KEY_LABEL,
                    anchor="md",
                )
    for m in range(LOWEST, HIGHEST + 1):
        if is_black(m):
            fr.black_key(d, m, BLACK_KEY)

    d.rectangle((0, 0, fr.w, 6 * s), fill=TRACK)
    d.text(
        (fr.w / 2, 52 * s),
        fit(title, sans(26 * s, 600), 760 * s),
        font=sans(26 * s, 600),
        fill=TEXT,
        anchor="mt",
    )
    d.text((fr.w / 2, 92 * s), subtitle, font=mono(18 * s), fill=MUTED, anchor="mt")
    d.text((64 * s, 48 * s), "LEFT HAND · CHORDS", font=mono(18 * s), fill=MUTED, anchor="lt")
    d.text(
        (fr.w - 64 * s, 48 * s), "RIGHT HAND · VOCALS", font=mono(18 * s), fill=MUTED, anchor="rt"
    )
    return img


def fit(text: str, f: ImageFont.FreeTypeFont, max_w: float) -> str:
    if f.getlength(text) <= max_w:
        return text
    while text and f.getlength(text + "…") > max_w:
        text = text[:-1]
    return text + "…"


def bars_from_score(score: dict) -> list[Bar]:
    bars = [
        Bar(c["start"], c["end"], p, "L", c["note_names"][i])
        for c in score["chords"]
        for i, p in enumerate(c["notes"])
    ]
    bars += [Bar(n["start"], n["end"], n["pitch"], "R", n["name"]) for n in score["melody"]]
    return sorted(bars, key=lambda b: b.start)


class Timeline:
    """Answers "what is sounding now, and what comes next?" for a sorted list of labelled spans."""

    def __init__(self, spans: list[tuple[float, float, str]]):
        self.spans = sorted(spans)
        self.starts = [sp[0] for sp in self.spans]

    def at(self, t: float) -> tuple[str, str]:
        i = bisect_right(self.starts, t) - 1
        now = self.spans[i][2] if i >= 0 and t < self.spans[i][1] else "–"
        for _, _, label in self.spans[i + 1 :]:
            if label != now:
                return now, label
        return now, "–"


def render_video(
    score: dict,
    audio_path: Path,
    out_path: Path,
    width: int = BASE_W,
    fps: int = 30,
    on_progress: Callable[[float], None] | None = None,
) -> None:
    fr = Frame(width)
    tempo = f" · {round(score['tempo'])} BPM" if score.get("tempo") else ""
    bg = background(fr, score["title"], f"Key {score['key']}{tempo}")
    bars = bars_from_score(score)
    chord_line = Timeline([(c["start"], c["end"], c["name"]) for c in score["chords"]])
    melody_line = Timeline([(n["start"], n["end"], n["name"]) for n in score["melody"]])
    duration = float(score["duration"])
    n_frames = max(1, int(duration * fps))

    cmd = [
        ffmpeg_exe(),
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{fr.w}x{fr.h}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-i",
        str(audio_path),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    active: list[Bar] = []
    nxt = 0
    try:
        for i in range(n_frames):
            t = i / fps
            while nxt < len(bars) and bars[nxt].start < t + LOOKAHEAD_S:
                active.append(bars[nxt])
                nxt += 1
            active = [b for b in active if b.end > t]
            img = draw_frame(
                fr, bg, active, t, duration, score["chords"], chord_line.at(t), melody_line.at(t)
            )
            proc.stdin.write(img.tobytes())
            if on_progress and i % fps == 0:
                on_progress(i / n_frames)
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
    if proc.wait() != 0:
        raise PipelineError(f"Video encoding failed: {err.strip()[-300:]}")
    if on_progress:
        on_progress(1.0)


def draw_frame(
    fr: Frame,
    bg: Image.Image,
    active: list[Bar],
    t: float,
    duration: float,
    chords: list[dict],
    chord_hud: tuple[str, str],
    note_hud: tuple[str, str],
) -> Image.Image:
    s = fr.s
    img = bg.copy()
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, fr.w * min(1.0, t / duration), 6 * s), fill=TEXT)

    lit: dict[int, tuple[int, int, int]] = {}
    for b in active:
        x, w = fr.keys[b.pitch]
        black = is_black(b.pitch)
        color, dark = HAND_COLORS[b.hand]
        y_bottom = min(fr.fall_h, fr.fall_h - (b.start - t) * fr.pps)
        # The gap at the note's end keeps repeated notes from merging into one bar.
        y_top = max(0.0, fr.fall_h - (b.end - t) * fr.pps + 3 * s)
        if y_bottom - y_top < 1:
            continue
        if b.start <= t:
            lit[b.pitch] = dark if black else color
        pad = (1 if black else 3) * s
        d.rounded_rectangle(
            (x + pad, y_top, x + w - pad, y_bottom), radius=6 * s, fill=dark if black else color
        )
        if y_bottom - y_top > 28 * s:
            label_font = mono((11 if black else 14) * s, 700)
            d.text((x + w / 2, y_bottom - 6 * s), b.label, font=label_font, fill=BG, anchor="md")

    tags = []
    for c in chords:
        if c["start"] > t + LOOKAHEAD_S or c["end"] <= t or not c["notes"]:
            continue
        tag_y = min(fr.fall_h, fr.fall_h - (c["start"] - t) * fr.pps) - 44 * s
        if tag_y > 0:
            tags.append((tag_y, c))
    # Top (upcoming) tags win; a tag that would overlap the one above it is skipped.
    last_bottom = 0.0
    for tag_y, c in sorted(tags, key=lambda tag: tag[0]):
        if tag_y < last_bottom:
            continue
        last_bottom = tag_y + 42 * s
        f = mono(22 * s, 700)
        right = fr.keys[min(c["notes"])][0] - 12 * s
        tw = f.getlength(c["name"])
        d.rounded_rectangle(
            (right - tw - 24 * s, tag_y, right, tag_y + 38 * s),
            radius=8 * s,
            fill=TEAL_TAG,
            outline=TEAL,
            width=max(1, round(s)),
        )
        d.text((right - 12 * s, tag_y + 19 * s), c["name"], font=f, fill=TEAL_TEXT, anchor="rm")

    if lit:
        for m, color in lit.items():
            if not is_black(m):
                fr.white_key(d, m, color)
        for m in range(LOWEST, HIGHEST + 1):
            if is_black(m):
                fr.black_key(d, m, lit.get(m, BLACK_KEY))

    hud(d, fr, 64 * s, "l", chord_hud, TEAL_TEXT)
    hud(d, fr, fr.w - 64 * s, "r", note_hud, AMBER)
    return img


def hud(
    d: ImageDraw.ImageDraw, fr: Frame, x: float, side: str, values: tuple[str, str], color
) -> None:
    s = fr.s
    now, nxt = values
    if now == "–":
        # Nothing sounding: a quiet dash instead of a giant coloured bar.
        d.text((x, 78 * s), now, font=sans(96 * s, 400), fill=HIT_LINE, anchor=f"{side}t")
    else:
        d.text((x, 78 * s), now, font=sans(96 * s, 700), fill=color, anchor=f"{side}t")
    label, value = "next ", nxt
    f_label, f_value = sans(24 * s), sans(24 * s, 600)
    if side == "l":
        d.text((x, 190 * s), label, font=f_label, fill=MUTED, anchor="lt")
        d.text((x + f_label.getlength(label), 190 * s), value, font=f_value, fill=TEXT, anchor="lt")
    else:
        d.text((x, 190 * s), value, font=f_value, fill=TEXT, anchor="rt")
        d.text(
            (x - f_value.getlength(value), 190 * s), label, font=f_label, fill=MUTED, anchor="rt"
        )
