"""Video ingestion: download from YouTube or save uploads, extract frames.

Frame extraction is scene-aware: ffmpeg's scene filter finds moments where the
footage changes (where an incident is most likely to occur), and up to
MAX_FRAMES are sampled around those changes. Static clips fall back to even
sampling across the duration.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("app.callanalysis.video")

MAX_FRAMES = 12
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

# YouTube bot-protection intermittently 403s the media URLs of some player
# clients (the web client now requires PO tokens on many networks). Trying the
# Android client is the most reliable anonymous fallback; keep the full chain
# so a working client is always attempted.
PLAYER_CLIENTS = ("default", "android", "tv", "ios", "web_embedded")
VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov"}


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr[-800:]}")


def validate_youtube_url(url: str) -> str:
    """Allow only https YouTube links (SSRF guard before handing off to yt-dlp)."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in YOUTUBE_HOSTS:
        raise ValueError(
            "Only https YouTube links are supported (youtube.com, youtu.be, m.youtube.com)."
        )
    return url.strip()


def download_youtube(url: str, work_dir: Path) -> Path:
    """Download a YouTube video to work_dir/video.mp4 via yt-dlp.

    Retries across player clients because YouTube's web client often returns
    403 on the media stream while other clients (android) still work.
    """
    import yt_dlp

    url = validate_youtube_url(url)
    errors: list[str] = []
    for client in PLAYER_CLIENTS:
        opts = {
            "outtmpl": str(work_dir / "video.%(ext)s"),
            "format": "bv*[height<=720]+ba/b[height<=720]/b",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if client != "default":
            opts["extractor_args"] = {"youtube": {"player_client": [client]}}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            break
        except Exception as e:
            errors.append(f"{client}: {e}")
            logger.warning("yt-dlp client %r failed — trying next", client)
            for partial in work_dir.glob("video.*.part"):
                partial.unlink(missing_ok=True)
    else:
        raise RuntimeError("Failed to download video from YouTube: " + "; ".join(errors[-2:]))

    candidates = [p for p in sorted(work_dir.glob("video.*")) if p.suffix in VIDEO_SUFFIXES]
    if not candidates:
        raise RuntimeError("yt-dlp finished but no video file was produced.")
    # Normalize to .mp4 for ffmpeg's benefit
    target = work_dir / "video.mp4"
    if candidates[0].suffix != ".mp4":
        _run(["ffmpeg", "-y", "-i", str(candidates[0]), "-c", "copy", str(target)])
        candidates[0].unlink()
    return target


def save_upload(upload_path: Path, work_dir: Path) -> Path:
    """Move an uploaded video into the job directory as video.mp4."""
    target = work_dir / "video.mp4"
    shutil.move(str(upload_path), str(target))
    return target


def _scene_timestamps(video_path: Path, threshold: float = 0.25) -> list[float]:
    """Detect scene-change timestamps via ffmpeg's scene filter."""
    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    return sorted(float(m) for m in re.findall(r"pts_time:([\d.]+)", proc.stderr))


def _pick_even(timestamps: list[float], count: int) -> list[float]:
    """Evenly spaced timestamps, deduped and sorted."""
    unique = sorted({round(ts, 1) for ts in timestamps})
    if len(unique) <= count:
        return unique
    indices = sorted({round(i * (len(unique) - 1) / (count - 1)) for i in range(count)})
    return [unique[i] for i in indices]


def extract_frames(video_path: Path, work_dir: Path) -> list[dict]:
    """Extract up to MAX_FRAMES frames, biased toward scene changes.

    Returns [{timestamp, file}] with timestamps in seconds.
    """
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = 0.0

    if duration <= 0:
        raise RuntimeError("Could not determine video duration.")

    scenes = _scene_timestamps(video_path)
    if scenes:
        timestamps = _pick_even([0.0] + scenes + [max(0.0, duration - 0.2)], MAX_FRAMES)
    else:
        timestamps = _pick_even(
            [i * (duration - 1) / (MAX_FRAMES - 1) for i in range(MAX_FRAMES)],
            MAX_FRAMES,
        )

    frames = []
    for i, timestamp in enumerate(timestamps):
        out_path = frames_dir / f"frame_{i + 1:04d}.jpg"
        # Seeking to the very end of a file can land past the video stream's
        # last frame (container duration > stream duration), which makes the
        # mjpeg encoder fail. Retry slightly earlier before giving up on a ts.
        attempts = [timestamp]
        if timestamp > 0.5:
            attempts.append(timestamp - 0.4)
        for attempt in attempts:
            try:
                _run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        f"{attempt:.1f}",
                        "-i",
                        str(video_path),
                        "-frames:v",
                        "1",
                        "-vf",
                        "scale=640:-2",
                        "-q:v",
                        "4",
                        str(out_path),
                        "-loglevel",
                        "error",
                    ]
                )
                frames.append({"timestamp": attempt, "file": str(out_path)})
                break
            except RuntimeError:
                logger.warning("Frame extraction failed at %.1fs", attempt)
        else:
            logger.warning("Skipping frame at %.1fs (ffmpeg could not encode it)", timestamp)
    if not frames:
        raise RuntimeError("Could not extract any frames from the video.")
    logger.info(
        "Extracted %d frames from %.0fs video (%d scenes detected)",
        len(frames),
        duration,
        len(scenes),
    )
    return frames


def cleanup(work_dir: Path) -> None:
    """Remove a job's working directory."""
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
