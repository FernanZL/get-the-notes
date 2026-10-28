# Get the Notes

Upload a song, get back a YouTube-style piano tutorial video: falling notes on an
88-key keyboard, **left hand = chords** (teal, with chord names) and **right hand =
the vocal melody** (amber, with note names). The soundtrack is a piano playing
exactly those notes (not the original recording), so you can check them by ear. You also
get the melody and chords as MIDI files and everything as `notes.json`.

Design canvas: https://claude.ai/artifact/UJbCvECEsyq1APFUFhDoZf

## How it works

| Step | Tool | Code |
| --- | --- | --- |
| Decode upload to 44.1 kHz WAV | ffmpeg | `backend/src/get_the_notes/pipeline/audio.py` |
| Split vocals / accompaniment | Demucs `htdemucs` (CPU) | `pipeline/separate.py` |
| Vocal melody → single line in C4–C6 | basic-pitch (ONNX) + cleanup | `pipeline/melody.py` |
| Chords, key, tempo | librosa beat-synced chroma, templates + Viterbi | `pipeline/chords.py`, `pipeline/theory.py` |
| Left-hand voicings in C2–B3 | smooth voice leading | `pipeline/voicing.py` |
| MIDI export | pretty_midi | `pipeline/midi.py` |
| Piano soundtrack of the transcription | FluidSynth + FluidR3 GM soundfont (additive fallback) | `pipeline/synth.py` |
| 1080p30 video | Pillow frames piped into ffmpeg/x264 | `pipeline/render.py` |

The API (`api.py`) stores uploads under `data/jobs/<id>/` and enqueues an RQ job; the
worker (`worker.py`) runs the pipeline and reports stage progress, which the React
frontend polls.

## Run with Docker

Requires Docker Desktop with WSL integration enabled for your distro
(Settings → Resources → WSL integration).

```sh
docker compose up --build
# open http://localhost:8080
```

Services: `web` (nginx serving the built frontend, proxying `/api`), `api` (FastAPI),
`worker` (RQ, does the heavy lifting), `redis`. Job files live in the `data` volume.

## Run locally (no Docker)

```sh
# 1. Redis (any way you like), e.g.
docker run --rm -p 6379:6379 redis:7-alpine

# 2. Backend
cd backend
uv sync
uv run uvicorn get_the_notes.api:app --reload --port 8000
uv run rq worker gtn               # in another terminal

# 3. Frontend
cd frontend
npm install
npm run dev                         # http://localhost:5173, proxies /api to :8000
```

ffmpeg is taken from your `PATH` if present, otherwise the static binary bundled with
`imageio-ffmpeg` is used.

Process a file straight from the command line, without Redis or the web UI:

```sh
cd backend
uv run get-the-notes path/to/song.mp3 -o out/
```

## Tests

```sh
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm run build
```

## Configuration

Environment variables (prefix `GTN_`): `GTN_DATA_DIR` (default `data`),
`GTN_REDIS_URL` (default `redis://localhost:6379/0`), `GTN_MAX_UPLOAD_MB` (100),
`GTN_MAX_DURATION_S` (900), `GTN_JOB_TIMEOUT_S` (7200).

## Notes

- basic-pitch pins TensorFlow < 2.15, which breaks with NumPy 2, so TensorFlow is
  excluded via `[tool.uv] override-dependencies` and basic-pitch runs its ONNX model.
- `setuptools<81` is pinned because `resampy` (a basic-pitch dependency) still imports
  `pkg_resources`.
