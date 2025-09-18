import subprocess
import os
import ffmpeg

def reverse_last_frames(video_path, duration_difference):
    last_segment_path = "last_segment.mp4"
    extended_video_path = "extended_video.mp4"

    # Extract last N seconds of the video
    cmd_extract = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-sseof", f"-{duration_difference}",
        "-i", video_path,
        "-c", "copy",
        last_segment_path
    ]
    subprocess.run(cmd_extract, check=True)

    # Reverse the last segment
    reversed_segment_path = "last_segment_reversed.mp4"
    cmd_reverse = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-i", last_segment_path,
        "-vf", "reverse",
        reversed_segment_path
    ]
    subprocess.run(cmd_reverse, check=True)

    # Create a concat file
    concat_file = "concat_list.txt"
    with open(concat_file, "w") as f:
        f.write(f"file '{os.path.abspath(video_path)}'\n")
        f.write(f"file '{os.path.abspath(reversed_segment_path)}'\n")

    # Concatenate video
    cmd_concat = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        extended_video_path
    ]
    subprocess.run(cmd_concat, check=True)

    # Cleanup
    os.remove(last_segment_path)
    os.remove(reversed_segment_path)
    os.remove(concat_file)

    return extended_video_path

def freeze_last_frame(video_path, duration_difference):
    last_frame_path = "last_frame.png"
    freeze_segment_path = "freeze_segment.mp4"
    extended_video_path = "extended_video.mp4"

    # Extract the very last frame as an image
    cmd_frame = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-sseof", "-0.1",          # seek to 1s from the end
        "-i", video_path,
        "-vframes", "1",         # just 1 frame
        last_frame_path
    ]
    subprocess.run(cmd_frame, check=True)

    # Turn the still image into a video segment of duration_difference seconds
    cmd_freeze = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-loop", "1",            # loop image
        "-i", last_frame_path,
        "-t", str(duration_difference),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        freeze_segment_path
    ]
    subprocess.run(cmd_freeze, check=True)

    # Create concat file
    concat_file = "concat_list.txt"
    with open(concat_file, "w") as f:
        f.write(f"file '{os.path.abspath(video_path)}'\n")
        f.write(f"file '{os.path.abspath(freeze_segment_path)}'\n")

    # Concatenate original video + frozen frame video
    cmd_concat = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        extended_video_path
    ]
    subprocess.run(cmd_concat, check=True)

    # Cleanup
    os.remove(last_frame_path)
    os.remove(freeze_segment_path)
    os.remove(concat_file)

    return extended_video_path

def swap_audio(video_path: str, audio_path: str, translation_type: str, output_path="temp/swapped_audio.mp4"):
    """
    Replace the audio track of a video with a new audio file, extending the video if
    the audio is longer.

    If the provided audio is longer than the original video, the video is extended
    by appending a reversed version of its last segment to match the audio duration.
    The extended video is then combined with the new audio track.

    Args:
        video_path (str): Path to the input video file (e.g., ".mp4").
        audio_path (str): Path to the replacement audio file (e.g., ".wav" or ".mp3").
        translation_type (str): 'Dub' or 'LipSync'. For dubbing, freeze last frame.
        output_path (str, optional): Path to save the final output video.

    Returns:
        output_path (str): Path to output video

    Example:
        >>> swap_audio("input.mp4", "new_audio.wav", "output.mp4")
        # Produces an "output.mp4" with the new audio track, extending
        # the video if necessary.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")
    
    # Probe video and audio
    probe_video = ffmpeg.probe(video_path)
    probe_audio = ffmpeg.probe(audio_path)

    video_duration = float(probe_video['format']['duration'])
    audio_duration = float(probe_audio['format']['duration'])

    duration_difference = audio_duration - video_duration

    if duration_difference > 0:

        if translation_type.lower() == 'dub':
            extended_video_path = freeze_last_frame(video_path, duration_difference)
        elif translation_type.lower() == 'lipsync':
            extended_video_path = reverse_last_frames(video_path, duration_difference)
        else:
            raise ValueError(f"Invalid translation type: {translation_type}.")

        # Replace audio
        cmd_final = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", extended_video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_final, check=True)

        # Clean up
        os.remove(extended_video_path)

    else:

        padded_audio_path = "padded_audio.wav"

        # Pad audio with silence at the end
        cmd_pad = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", audio_path,
            "-af", f"apad=pad_dur={video_duration}",
            "-t", str(video_duration),  # enforce duration match
            padded_audio_path
        ]
        subprocess.run(cmd_pad, check=True)

        # Replace audio with padded version
        cmd_final = [
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-i", padded_audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_final, check=True)

        # Cleanup
        os.remove(padded_audio_path)

    return output_path