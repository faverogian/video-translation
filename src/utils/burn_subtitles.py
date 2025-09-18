import subprocess
import os

def burn_subtitles(video_path: str, srt_path: str, output_path: str = "temp/subtitled.mp4"):
    """
    Burn subtitles into a video from a list of srt.Subtitle objects.

    Args:
        video_path (str): Path to the input video.
        srt_path (str): Path to subtitle srt file.
        output_path (str): Path to save the output video with burned-in subtitles.

    Returns:
        output_path (str): Path to output video
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.exists(srt_path):
        raise FileNotFoundError(f"Subtitles not found: {srt_path}")

    # Burn subtitles into video
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}:charenc=UTF-8",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "veryfast",
        "-c:a", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)

    return output_path
