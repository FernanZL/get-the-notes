"""Vocal / accompaniment separation with Demucs."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

MODEL_NAME = "htdemucs"


def load_model():
    from demucs.pretrained import get_model

    model = get_model(MODEL_NAME)
    model.eval()
    return model


def separate(
    wav_path: Path,
    out_dir: Path,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[Path, Path]:
    """Split a 44.1 kHz stereo WAV into vocals.wav and no_vocals.wav inside out_dir."""
    from demucs.apply import apply_model

    model = load_model()
    audio, sr = sf.read(str(wav_path), dtype="float32", always_2d=True)
    if sr != model.samplerate:
        raise ValueError(f"expected {model.samplerate} Hz audio, got {sr}")

    mix = torch.from_numpy(audio.T.copy())  # (channels, samples)
    ref = mix.mean(0)
    mean, std = ref.mean(), ref.std() + 1e-8
    length = mix.shape[-1]

    def callback(info: dict) -> None:
        if on_progress and info.get("state") == "end":
            on_progress(min(1.0, info.get("segment_offset", 0) / length))

    with torch.no_grad():
        sources = apply_model(
            model,
            ((mix - mean) / std)[None],
            split=True,
            overlap=0.25,
            device="cpu",
            callback=callback,
        )[0]
    sources = sources * std + mean

    vocals_idx = model.sources.index("vocals")
    vocals = sources[vocals_idx]
    accompaniment = sources.sum(0) - vocals

    out_dir.mkdir(parents=True, exist_ok=True)
    vocals_path, accomp_path = out_dir / "vocals.wav", out_dir / "no_vocals.wav"
    for path, stem in ((vocals_path, vocals), (accomp_path, accompaniment)):
        data = np.clip(stem.numpy().T, -1.0, 1.0)
        sf.write(str(path), data, sr, subtype="PCM_16")
    if on_progress:
        on_progress(1.0)
    return vocals_path, accomp_path
