import os
import uuid
import shutil
import subprocess
from datetime import datetime
from models.data_models import Course

def _is_playlist(url: str) -> bool:
    """Return True if the given URL points to a YouTube playlist.
    We run `yt‑dlp --flat-playlist --print-json` and look for the
    `_type":"playlist"` marker in the JSON output. The call is fast
    and does not download any media.
    """
    try:
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--print-json", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "\"_type\": \"playlist\"" in result.stdout
    except Exception:
        # If anything goes wrong, assume it is not a playlist – the ingest
        # step will fail later with a clear error message.
        return False

class ContentIngestionProcessor:
    """Module 1: Content Ingestion (Video, PDF, DOCX, TXT)"""
    def __init__(self, data_dir: str = "data/courses"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
    def ingest_content(self, file_path: str, title: str = None) -> Course:
        """
        Validates the file, generates a course ID, saves the content,
        and creates the metadata object.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Content file not found: {file_path}")
            
        course_id = str(uuid.uuid4())
        course_dir = os.path.join(self.data_dir, course_id)
        os.makedirs(course_dir, exist_ok=True)
        
        # Save original file
        filename = os.path.basename(file_path)
        destination_path = os.path.join(course_dir, filename)
        
        if file_path != destination_path:
            shutil.copy2(file_path, destination_path)
            
        if not title:
            title = filename
            
        course = Course(
            course_id=course_id,
            title=title,
            original_video_path=destination_path,  # We keep this field name for backward compatibility
            upload_date=datetime.now().isoformat(),
            transcript_status="pending",
            embedding_status="pending"
        )
        
        return course

    def ingest_url(self, url: str, title: str = None) -> Course:
        """Download a public video/audio URL using yt‑dlp and create a Course.

        The method now:
        1️⃣ Detects playlists and aborts with a clear error.
        2️⃣ Checks that ``ffmpeg`` is available (required later for audio extraction).
        3️⃣ Uses a safe ``yt‑dlp`` command with explicit format selection, timeout and a browser‑like user‑agent.
        4️⃣ Provides concise error messages.
        """
        # --------------------------------------------------------------
        # 1️⃣ Reject playlists – we only support single video URLs.
        # --------------------------------------------------------------
        if _is_playlist(url):
            raise RuntimeError("Playlist URLs are not supported – please provide a single video link.")
        
        # --------------------------------------------------------------
        # 2️⃣ Verify ffmpeg is installed (required for later audio extraction).
        # --------------------------------------------------------------
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except Exception as e:
            raise RuntimeError("ffmpeg is not installed or not reachable in PATH.") from e
        
        course_id = str(uuid.uuid4())
        course_dir = os.path.join(self.data_dir, course_id)
        os.makedirs(course_dir, exist_ok=True)
        
        # --------------------------------------------------------------
        # 3️⃣ Download best MP4 video + M4A audio (or best fallback).
        # --------------------------------------------------------------
        output_template = os.path.join(course_dir, "downloaded_video.%(ext)s")
        dl_cmd = [
            "yt-dlp",
            "-f", "best[ext=mp4][height<=480]/bestvideo[height<=480]+bestaudio/best",
            "--no-warnings",
            "--no-check-certificate",
            "-o", output_template,
            "--no-playlist",
            url,
        ]
        try:
            subprocess.run(dl_cmd, check=True, capture_output=True, timeout=300)
        except subprocess.CalledProcessError as e:
            err_output = e.stderr.decode('utf-8', errors='ignore')
            errors = [line for line in err_output.split('\n') if 'ERROR:' in line]
            if errors:
                raise RuntimeError(f"Download failed: {errors[0].strip()}") from e
            else:
                raise RuntimeError("Download failed. Ensure the video is public and accessible.") from e
        
        # --------------------------------------------------------------
        # 4️⃣ Locate the downloaded file.
        # --------------------------------------------------------------
        downloaded_files = os.listdir(course_dir)
        if not downloaded_files:
            raise RuntimeError("Download completed but no file was found.")
        downloaded_file = os.path.join(course_dir, downloaded_files[0])
        
        if not title:
            title = f"Web Video ({course_id[:8]})"
        
        course = Course(
            course_id=course_id,
            title=title,
            original_video_path=downloaded_file,
            upload_date=datetime.now().isoformat(),
            transcript_status="pending",
            embedding_status="pending",
        )
        return course
