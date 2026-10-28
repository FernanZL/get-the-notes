FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 fluidsynth fluid-soundfont-gm \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    TORCH_HOME=/models/torch \
    HF_HOME=/models/huggingface \
    NUMBA_CACHE_DIR=/tmp/numba \
    GTN_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first so code changes don't reinstall torch.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Bake the Demucs weights into the image so the first job doesn't download them.
RUN python -c "from get_the_notes.pipeline.separate import load_model; load_model()"

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data && chown app /data \
    && chmod -R a+rX /models
USER app

EXPOSE 8000
CMD ["uvicorn", "get_the_notes.api:app", "--host", "0.0.0.0", "--port", "8000"]
