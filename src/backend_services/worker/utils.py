import os
from pathlib import Path
import subprocess
import shlex
import logging

logger = logging.getLogger(__name__)


def get_video_size(path: str) -> int:
    """Return the size of the file"""
    try:
        return os.path.getsize(path)
    except OSError as e:
        logger.error(f"Error getting size for file {path}: {e}")
        return -1
    

def get_video_length(filename: str) -> int:
    """Get duration of video file in seconds"""
    try:
        output = subprocess.check_output((
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", filename
        ))
        return int(float(output))
    except Exception as e:
        logger.error(f"Error getting video length: {e}")
        raise


def split_video_by_seconds(filename, split_length, output_dir, vcodec="copy", acodec="copy",
                           extra="", video_length=None):
    """Split video into chunks of specified length in seconds."""
    
    if split_length <= 0:
        raise ValueError("split_length must be greater than 0")
    
    if video_length is None:
        video_length = get_video_length(filename)

    split_count = int(video_length / split_length) + (1 if video_length % split_length > 0 else 0)

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    split_cmd = ["ffmpeg", "-i", filename, "-vcodec", vcodec, "-acodec", acodec] + shlex.split(extra)
    for i in range(split_count):
        start_time = i * split_length
        output_file = os.path.join(output_dir, f"part_{i:03d}.mp4")
        cmd = split_cmd + ["-ss", str(start_time), "-t", str(split_length), output_file]
        subprocess.run(cmd, check=True)





def transcode_to_resolution(input_path: Path,output_path: Path,resolution: str = "1080p",bitrate: int = 5000
    ) -> bool:
        """Transcode chunk to target resolution."""
        try:
            # Parse resolution (e.g., "1080p" -> 1080)
            height = int(resolution.rstrip('p'))
            
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", str(input_path),
                "-vf", f"scale=-1:{height}",  # Scale to target height, maintain aspect ratio
                "-c:v", "libx264",
                "-preset", "fast",  # fast for worker speed
                "-b:v", f"{bitrate}k",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path),
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result
        
        except Exception as e:
            raise