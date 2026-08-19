"""Job store + orchestration for Call Review analysis.

Jobs run on a background thread so the API returns immediately; the frontend
polls GET /calls/{id}. Job state is persisted in PostgreSQL (survives
restarts); a startup sweep marks interrupted jobs as failed.
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.callanalysis import laws, video, vision
from app.database import SessionLocal
from app.models import CallJob

logger = logging.getLogger("app.callanalysis.analyzer")

UPLOAD_DIR = Path("data/uploads")
JOB_TIMEOUT_SECONDS = 10 * 60


@dataclass
class Job:
    id: str
    source_type: str  # "youtube" | "upload"
    source: str
    note: str = ""
    competition: str = "La Liga"
    decision_type: str = "auto"
    status: str = "queued"  # queued | extracting | analyzing | done | error
    progress: float = 0.0
    error: str | None = None
    result: dict | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    uploaded_path: str | None = None


class JobStore:
    """Persistent job store. Pass session_factory=None for in-memory (tests)."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._mem: dict[str, Job] = {}

    def create(
        self,
        source_type: str,
        source: str,
        note: str = "",
        competition: str = "La Liga",
        decision_type: str = "auto",
        uploaded_path: str | None = None,
    ) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            source_type=source_type,
            source=source,
            note=note,
            competition=competition,
            decision_type=decision_type,
            uploaded_path=uploaded_path,
        )
        self._upsert(job)
        threading.Thread(target=self._run, args=(job,), daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        if self._session_factory is None:
            return self._mem.get(job_id)
        session = self._session_factory()
        try:
            row = session.get(CallJob, job_id)
            return self._row_to_job(row) if row else None
        finally:
            session.close()

    def list_jobs(self, limit: int = 10) -> list[Job]:
        if self._session_factory is None:
            return sorted(self._mem.values(), key=lambda j: j.created_at, reverse=True)[:limit]
        session = self._session_factory()
        try:
            rows = session.query(CallJob).order_by(CallJob.created_at.desc()).limit(limit).all()
            return [self._row_to_job(row) for row in rows]
        finally:
            session.close()

    def delete(self, job_id: str) -> bool:
        if self._session_factory is None:
            return self._mem.pop(job_id, None) is not None
        session = self._session_factory()
        try:
            row = session.get(CallJob, job_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    def mark_interrupted(self, message: str) -> int:
        """Mark in-flight jobs as failed (called at startup after a restart)."""
        if self._session_factory is None:
            return 0
        session = self._session_factory()
        try:
            count = (
                session.query(CallJob)
                .filter(CallJob.status.in_(["queued", "extracting", "analyzing"]))
                .update(
                    {
                        CallJob.status: "error",
                        CallJob.error: message,
                        CallJob.updated_at: datetime.now(timezone.utc),
                    },
                    synchronize_session=False,
                )
            )
            session.commit()
            return int(count)
        finally:
            session.close()

    def cleanup(self, older_than_hours: int = 24) -> list[str]:
        """Delete old jobs and return their ids (caller removes files)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        if self._session_factory is None:
            expired = [
                job_id
                for job_id, job in self._mem.items()
                if datetime.fromisoformat(job.created_at) < cutoff
            ]
            for job_id in expired:
                self._mem.pop(job_id, None)
            return expired
        session = self._session_factory()
        try:
            rows = session.query(CallJob).filter(CallJob.created_at < cutoff).all()
            ids = [row.id for row in rows]
            for row in rows:
                session.delete(row)
            session.commit()
            return ids
        finally:
            session.close()

    # ------------------------------------------------------------------

    def _row_to_job(self, row: CallJob) -> Job:
        return Job(
            id=row.id,
            source_type=row.source_type,
            source=row.source,
            note=row.note or "",
            competition=row.competition,
            decision_type=row.decision_type,
            status=row.status,
            progress=float(row.progress or 0.0),
            error=row.error,
            result=row.result,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )

    def _upsert(self, job: Job) -> None:
        if self._session_factory is None:
            self._mem[job.id] = job
            return
        session = self._session_factory()
        try:
            row = session.get(CallJob, job.id)
            if row is None:
                row = CallJob(
                    id=job.id,
                    source_type=job.source_type,
                    source=job.source,
                    note=job.note,
                    competition=job.competition,
                    decision_type=job.decision_type,
                    status=job.status,
                    progress=job.progress,
                    error=job.error,
                    result=job.result,
                )
                session.add(row)
            else:
                row.status = job.status
                row.progress = job.progress
                row.error = job.error
                row.result = job.result
            session.commit()
        finally:
            session.close()

    def _update(self, job: Job, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc).isoformat()
        self._upsert(job)

    def _run(self, job: Job) -> None:
        work_dir = UPLOAD_DIR / job.id
        work_dir.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + JOB_TIMEOUT_SECONDS

        def check_timeout(stage: str) -> None:
            if time.monotonic() > deadline:
                raise RuntimeError(f"Analysis timed out while {stage}.")

        try:
            self._update(job, status="extracting", progress=0.1)
            if job.source_type == "youtube":
                video_path = video.download_youtube(job.source, work_dir)
            else:
                if not job.uploaded_path:
                    raise RuntimeError("Uploaded video file is missing.")
                video_path = video.save_upload(Path(job.uploaded_path), work_dir)
            check_timeout("downloading")

            frames = video.extract_frames(video_path, work_dir)
            check_timeout("extracting frames")
            self._update(job, status="analyzing", progress=0.55)

            # The agent reads the applicable Laws of the Game before judging.
            rules_text = laws.get_laws_context(job.competition, job.decision_type)
            result = vision.analyze_frames(frames, context=job.note, rules_text=rules_text)
            check_timeout("analyzing")
            self._update(
                job,
                status="done",
                progress=1.0,
                result={
                    **result,
                    "frame_count": len(frames),
                    "job_id": job.id,
                    "competition": job.competition,
                    "frames": [
                        {"timestamp": f["timestamp"], "file": Path(f["file"]).name} for f in frames
                    ],
                },
            )
            logger.info("Call analysis %s complete: %s", job.id, result.get("verdict"))
        except Exception as e:
            logger.exception("Call analysis %s failed", job.id)
            self._update(job, status="error", error=str(e), progress=1.0)


store = JobStore(session_factory=SessionLocal)


def cleanup_old_jobs(older_than_hours: int = 24) -> int:
    """Delete expired jobs and their stored files. Returns count removed."""
    ids = store.cleanup(older_than_hours)
    for job_id in ids:
        video.cleanup(UPLOAD_DIR / job_id)
    if ids:
        logger.info("Cleaned up %d expired call-analysis jobs", len(ids))
    return len(ids)
