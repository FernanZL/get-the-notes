"""RQ job entrypoint. Enqueued by the API as "get_the_notes.worker.process_job"."""

import json
import logging

from rq import get_current_job

from .pipeline import PipelineError, overall_progress, run_pipeline
from .settings import settings

log = logging.getLogger(__name__)


def process_job(job_id: str) -> None:
    job = get_current_job()
    job_dir = settings.jobs_dir / job_id
    meta = json.loads((job_dir / "meta.json").read_text())

    def report(stage: str, fraction: float) -> None:
        if job is None:
            return
        job.meta.update(
            stage=stage,
            stage_progress=round(fraction, 3),
            progress=round(overall_progress(stage, fraction), 3),
        )
        job.save_meta()

    try:
        run_pipeline(
            job_dir,
            job_dir / meta["input"],
            meta["title"],
            report,
            max_duration_s=settings.max_duration_s,
        )
    except PipelineError as e:
        if job is not None:
            job.meta["error"] = str(e)
            job.save_meta()
        raise
    except Exception:
        log.exception("job %s failed", job_id)
        if job is not None:
            job.meta["error"] = "Something went wrong while processing this song."
            job.save_meta()
        raise
