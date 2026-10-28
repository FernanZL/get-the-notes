import json
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from .settings import settings

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
OUTPUT_FILES = {
    "video.mp4": "video/mp4",
    "melody.mid": "audio/midi",
    "chords.mid": "audio/midi",
    "notes.json": "application/json",
}
JOB_ID = re.compile(r"^[0-9a-f]{32}$")
CHUNK = 1024 * 1024

app = FastAPI(title="Get the Notes")


def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


def get_queue(redis: Annotated[Redis, Depends(get_redis)]) -> Queue:
    return Queue(settings.queue_name, connection=redis)


def job_dir(job_id: str) -> Path:
    if not JOB_ID.match(job_id):
        raise HTTPException(404, "Job not found")
    path = settings.jobs_dir / job_id
    if not path.is_dir():
        raise HTTPException(404, "Job not found")
    return path


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/jobs", status_code=201)
async def create_job(file: UploadFile, queue: Annotated[Queue, Depends(get_queue)]) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Upload an MP3, WAV, M4A, FLAC, OGG or AAC file.")

    job_id = uuid.uuid4().hex
    path = settings.jobs_dir / job_id
    path.mkdir(parents=True)
    input_name = f"input{ext}"
    limit = settings.max_upload_mb * CHUNK
    size = 0
    with open(path / input_name, "wb") as out:
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > limit:
                out.close()
                for p in path.iterdir():
                    p.unlink()
                path.rmdir()
                raise HTTPException(413, f"Files can be at most {settings.max_upload_mb} MB.")
            out.write(chunk)

    title = Path(file.filename or "Untitled").stem[:120]
    meta = {"input": input_name, "title": title, "filename": file.filename, "size": size}
    (path / "meta.json").write_text(json.dumps(meta))
    queue.enqueue(
        "get_the_notes.worker.process_job",
        job_id,
        job_id=job_id,
        job_timeout=settings.job_timeout_s,
        result_ttl=settings.result_ttl_s,
        failure_ttl=settings.result_ttl_s,
    )
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, redis: Annotated[Redis, Depends(get_redis)]) -> dict:
    path = job_dir(job_id)
    meta = json.loads((path / "meta.json").read_text())
    base = {"id": job_id, "title": meta["title"], "filename": meta.get("filename")}
    try:
        job = Job.fetch(job_id, connection=redis)
    except NoSuchJobError:
        # Redis forgot the job (expired or restarted); fall back to what's on disk.
        if (path / "video.mp4").exists():
            return base | {
                "status": "finished",
                "stage": "done",
                "stage_progress": 1.0,
                "progress": 1.0,
                "error": None,
            }
        raise HTTPException(404, "Job not found") from None

    status = job.get_status()
    status = status.value if hasattr(status, "value") else str(status)
    error = job.meta.get("error")
    if status == "failed" and not error:
        error = "Something went wrong while processing this song."
    finished = status == "finished"
    return base | {
        "status": status,
        "stage": "done" if finished else job.meta.get("stage", "queued"),
        "stage_progress": 1.0 if finished else job.meta.get("stage_progress", 0.0),
        "progress": 1.0 if finished else job.meta.get("progress", 0.0),
        "error": error,
    }


@app.get("/api/jobs/{job_id}/files/{name}")
def job_file(job_id: str, name: str, download: bool = False) -> FileResponse:
    if name not in OUTPUT_FILES:
        raise HTTPException(404, "File not found")
    path = job_dir(job_id) / name
    if not path.exists():
        raise HTTPException(404, "File not ready")
    filename = None
    if download:
        title = json.loads((path.parent / "meta.json").read_text())["title"]
        safe = re.sub(r"[^\w\- ]+", "", title).strip() or "tutorial"
        filename = f"{safe} - {name}"
    return FileResponse(path, media_type=OUTPUT_FILES[name], filename=filename)
