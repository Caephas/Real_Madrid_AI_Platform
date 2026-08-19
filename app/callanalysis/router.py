"""REST endpoints for Call Review: submit videos, poll jobs, view frames."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.callanalysis import video
from app.callanalysis.analyzer import UPLOAD_DIR, store
from app.callanalysis.video import validate_youtube_url

logger = logging.getLogger("app.callanalysis")

router = APIRouter(prefix="/calls", tags=["calls"])

MAX_UPLOAD_MB = 200
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    error: str | None = None
    result: dict | None = None


def _to_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        result=job.result,
    )


@router.post("/analyze", response_model=JobResponse)
async def analyze_call(
    youtube_url: str | None = Form(None),
    note: str | None = Form(None),
    video: UploadFile | None = None,
    competition: str = Form("La Liga"),
    decision_type: str = Form("auto"),
):
    """Analyze a match call from a YouTube link or an uploaded video file."""
    if not youtube_url and video is None:
        raise HTTPException(status_code=422, detail="Provide a youtube_url or an uploaded video.")

    if youtube_url:
        try:
            validate_youtube_url(youtube_url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    uploaded_path = None
    if video is not None:
        ext = Path(video.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=422, detail=f"Unsupported file type '{ext}'.")
        content = await video.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=422, detail=f"Video exceeds {MAX_UPLOAD_MB}MB.")

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # Never derive filesystem paths from the client-supplied filename.
        stored_name = f"{uuid.uuid4().hex}{ext}"
        uploaded_path = str(UPLOAD_DIR / stored_name)
        Path(uploaded_path).write_bytes(content)

    job = store.create(
        source_type="youtube" if youtube_url else "upload",
        source=youtube_url or video.filename or "upload",
        note=note or "",
        competition=competition,
        decision_type=decision_type,
        uploaded_path=uploaded_path,
    )
    logger.info("Created call analysis job %s (%s)", job.id, job.source_type)
    return _to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    """Poll a job's status and result."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _to_response(job)


@router.get("/{job_id}/frames/{filename}")
def get_frame(job_id: str, filename: str):
    """Serve an extracted frame for the result view (path-traversal safe)."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    work_dir = UPLOAD_DIR / job_id
    frame_path = (work_dir / "frames" / filename).resolve()
    if not frame_path.is_relative_to((work_dir / "frames").resolve()):
        raise HTTPException(status_code=400, detail="Invalid frame path.")
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame not found.")
    return FileResponse(frame_path, media_type="image/jpeg")


@router.delete("/{job_id}")
def delete_job(job_id: str):
    """Delete a job and its stored video/frames."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    video.cleanup(UPLOAD_DIR / job_id)
    if job.uploaded_path:
        Path(job.uploaded_path).unlink(missing_ok=True)
    store.delete(job_id)
    return {"deleted": True, "job_id": job_id}


@router.get("", response_model=list[JobResponse])
def list_jobs(limit: int = 10):
    """List recent analysis jobs (newest first)."""
    return [_to_response(job) for job in store.list_jobs(limit=min(limit, 50))]
