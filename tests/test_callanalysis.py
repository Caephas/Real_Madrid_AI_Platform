"""Unit tests for the Call Review module (video ingestion + job lifecycle)."""

import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

import app.callanalysis.analyzer as analyzer
import app.callanalysis.router as router_module
import app.callanalysis.vision as vision
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


def test_download_youtube_falls_back_to_android(tmp_path, monkeypatch):
    """When YouTube 403s the default player client, retry the android client."""

    class FakeYtDlp:
        attempts: list[str] = []

        class YoutubeDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def download(self, urls):
                client = (
                    self.opts.get("extractor_args", {})
                    .get("youtube", {})
                    .get("player_client", ["default"])[0]
                )
                FakeYtDlp.attempts.append(client)
                if client == "default":
                    raise RuntimeError("unable to download video data: HTTP Error 403")
                out = Path(self.opts["outtmpl"].replace("%(ext)s", "mp4"))
                out.write_bytes(b"fake-video")

    monkeypatch.setitem(sys.modules, "yt_dlp", FakeYtDlp)

    result = video.download_youtube("https://www.youtube.com/watch?v=abc123", tmp_path)

    assert FakeYtDlp.attempts == ["default", "android"]
    assert result == tmp_path / "video.mp4"
    assert result.read_bytes() == b"fake-video"


def test_extract_frames_retries_bad_timestamp(tmp_path, monkeypatch):
    """A seek past the stream's last frame is retried slightly earlier, not fatal."""
    duration = "4.0"

    def fake_run(cmd, **kwargs):
        if cmd[0] == "ffprobe":
            return types.SimpleNamespace(stdout=duration, stderr="", returncode=0)
        if "select='gt(scene," in " ".join(cmd):
            # Two scene changes plus the forced end timestamp (3.8) in the mix.
            return types.SimpleNamespace(
                stdout="", stderr="pts_time:0.5\npts_time:1.5\n", returncode=0
            )
        if "-frames:v" in cmd:
            # 3.8 sits past the video stream's end; everything else succeeds.
            if cmd[cmd.index("-ss") + 1] == "3.8":
                return types.SimpleNamespace(stdout="", stderr="", returncode=1)
            return types.SimpleNamespace(stdout="", stderr="", returncode=0)
        return types.SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    frames = video.extract_frames(video_path, tmp_path)

    timestamps = [f["timestamp"] for f in frames]
    assert 3.8 not in timestamps
    assert 3.4 in timestamps  # the retry at timestamp - 0.4
    assert len(frames) == 4  # 0.0 + 2 scene changes + the retried end timestamp


def test_analyze_frames_retries_transient_failure(tmp_path, monkeypatch):
    """A 500 from the vision API is retried before succeeding."""

    class FakeResponse:
        def __init__(self, status_code, body=None):
            self.status_code = status_code
            self._body = body

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "boom", request=None, response=self  # type: ignore[arg-type]
                )

        def json(self):
            return self._body

    import httpx

    calls = {"n": 0}

    def fake_post(url, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(500)
        return FakeResponse(
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"verdict":"correct_call","decision_type":"foul",'
                                    '"confidence":90,"summary":"ok","reasoning":[],'
                                    '"laws_cited":["Law 12"],"key_frames":[]}'
                                }
                            ]
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(vision.httpx, "post", fake_post)
    monkeypatch.setattr(vision.time, "sleep", lambda s: None)
    frame_file = tmp_path / "f.jpg"
    frame_file.write_bytes(b"jpeg")

    result = vision.analyze_frames([{"timestamp": 1.0, "file": str(frame_file)}])

    assert calls["n"] == 2
    assert result["verdict"] == "correct_call"


def test_analyze_frames_connect_error_is_clean(tmp_path, monkeypatch):
    """A connection error on the first attempt must not NameError on resp."""
    import httpx

    def fake_post(url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(vision.httpx, "post", fake_post)
    frame_file = tmp_path / "f.jpg"
    frame_file.write_bytes(b"jpeg")

    with pytest.raises(RuntimeError, match="Vision model unavailable"):
        vision.analyze_frames([{"timestamp": 1.0, "file": str(frame_file)}])


def test_vision_model_tracks_settings():
    from app.config import settings

    assert vision.VISION_MODEL == settings.gemini_model
