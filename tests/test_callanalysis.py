"""Unit tests for the Call Review module (video ingestion + job lifecycle)."""

import shutil
import subprocess

import pytest

import app.callanalysis.analyzer as analyzer
import app.callanalysis.router as router_module
from app.callanalysis import video
from app.callanalysis.analyzer import JobStore
from app.callanalysis.laws import get_laws_context
from app.callanalysis.video import validate_youtube_url


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _make_test_video(path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:duration=3",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        capture_output=True,
        check=True,
    )


@pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg/ffprobe not installed")
def test_extract_frames_samples_and_caps(tmp_path):
    video_path = tmp_path / "clip.mp4"
    _make_test_video(video_path)
    frames = video.extract_frames(video_path, tmp_path)
    assert len(frames) >= 3
    assert len(frames) <= video.MAX_FRAMES
    for frame in frames:
        assert 0 <= frame["timestamp"] <= 3
        assert __import__("pathlib").Path(frame["file"]).exists()


def test_job_store_error_path(tmp_path, monkeypatch):
    """A job with a missing upload fails cleanly and reports the error."""
    store = JobStore()
    job = store.create(
        source_type="upload",
        source="missing.mp4",
        uploaded_path=str(tmp_path / "does_not_exist.mp4"),
    )
    import time

    for _ in range(50):  # wait up to ~2.5s for the worker thread
        if job.status in ("done", "error"):
            break
        time.sleep(0.05)
    assert job.status == "error"
    assert "does_not_exist" in (job.error or "")


def test_job_requires_source(client):
    """POST /calls/analyze rejects requests without a URL or file."""
    resp = client.post("/calls/analyze")
    assert resp.status_code == 422


def test_unknown_job_returns_404(client):
    assert client.get("/calls/nope").status_code == 404


def test_youtube_url_allowlist_blocks_ssrf():
    assert validate_youtube_url("https://youtu.be/abc123") == "https://youtu.be/abc123"
    assert (
        validate_youtube_url("https://www.youtube.com/watch?v=x")
        == "https://www.youtube.com/watch?v=x"
    )
    for bad in (
        "http://youtu.be/x",
        "https://evil.com/x",
        "file:///etc/passwd",
        "https://127.0.0.1/x",
        "https://169.254.169.254/latest/meta-data",
    ):
        with pytest.raises(ValueError, match="YouTube"):
            validate_youtube_url(bad)


def test_upload_filename_never_used_in_path(client, tmp_path, monkeypatch):
    """Client filenames with traversal must not escape the uploads directory."""
    monkeypatch.setattr(router_module, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(analyzer, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(analyzer, "store", JobStore())  # in-memory, no DB in CI

    resp = client.post(
        "/calls/analyze",
        files={"video": ("../../evil.mp4", b"not-a-real-video", "video/mp4")},
    )
    assert resp.status_code == 200

    # Nothing may escape the uploads directory, regardless of the filename
    assert not (tmp_path.parent / "evil.mp4").exists()
    assert not any("evil" in str(f) for f in tmp_path.rglob("*"))


def test_laws_context_reads_relevant_laws():
    ctx = get_laws_context("UEFA Champions League", "penalty")
    assert "[Law 12]" in ctx
    assert "[Law 14]" in ctx
    assert "UEFA Champions League" in ctx
    assert "captain-only" in ctx
    assert "PENALTY" in ctx
    assert "READ THESE BEFORE JUDGING" in ctx
