import os
import sys 
import subprocess
import shlex


def get_video_size(path: str) -> int:
    """Return the size of the file"""
    try:
        return os.path.getsize(path)
    except OSError as e:
        print(f"Error getting size for file {path}: {e}", file=sys.stderr)
        return -1
    

def get_video_length(filename: str):
    """Stub function to return video length"""
    output = subprocess.check_output(("ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename))
    return int(float(output))


 
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


def convert_to_720p(input_file: str, output_file: str):
    """Convert video to 720p resolution."""
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-vf", "scale=-1:720",
        "-c:a", "copy",
        output_file
    ]
    subprocess.run(cmd, check=True)