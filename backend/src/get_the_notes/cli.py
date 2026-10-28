"""Run the pipeline on a local file without Redis: `get-the-notes song.mp3 -o out/`."""

import argparse
import shutil
from pathlib import Path

from .pipeline import overall_progress, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn a song into a piano tutorial video.")
    parser.add_argument("song", type=Path)
    parser.add_argument("-o", "--out", type=Path, default=Path("out"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    input_path = args.out / f"input{args.song.suffix.lower()}"
    shutil.copyfile(args.song, input_path)

    last = [""]

    def report(stage: str, fraction: float) -> None:
        line = f"{stage:<11} {overall_progress(stage, fraction):6.1%}"
        if line != last[0]:
            print(line, flush=True)
            last[0] = line

    run_pipeline(args.out, input_path, args.song.stem, report)
    print(f"Done: {args.out / 'video.mp4'}")
