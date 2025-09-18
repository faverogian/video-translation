import os
import srt
import datetime
from pydub import AudioSegment
from TTS.api import TTS
from tqdm import tqdm

class TextToSpeech:
    """
    A text-to-speech (TTS) utility using Coqui XTTS for generating speech
    from subtitle text and aligning the audio with updated subtitle timings.

    This class supports generating German audio (default) from English SRT
    subtitles and can output both the synthesized audio file and updated
    subtitle objects with adjusted timestamps.
    """

    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2", device: str = "cpu"):
        """
        Initialize the TextToSpeech engine with a Coqui XTTS model.

        Args:
            model_name (str, optional): Name of the Coqui TTS model to load.
                Defaults to "tts_models/multilingual/multi-dataset/xtts_v2".
            device (str, optional): The device on which to run the model
                ("cpu" or "cuda"). If not provided, defaults to "cpu".
        """
        self.device = device
        self.tts = TTS(model_name).to(self.device)

    def set_voice(self, target_voice: str):
        """
        Set the target speaker's voice using a reference audio sample.

        A short "hello world" clip is synthesized and saved to disk to
        initialize and confirm the chosen voice.

        Args:
            target_voice (str): Path to a reference WAV file of the target speaker.
        """
        self.tts.tts_to_file(
            text="Hello world",
            speaker_wav=target_voice,
            speaker="MySpeaker1",
            language="en",
            file_path="temp/hello_world.wav",
        )

    def srt_to_audio(self, subs: list[srt.Subtitle], output_file: str = "temp/de_audio.wav", speed: float = 1.0):
        """
        Convert SRT subtitles into synthesized speech audio, aligning subtitle
        timings to the generated audio duration.

        Each subtitle is synthesized in sequence, concatenated into a single
        audio file, and new subtitle timings are computed based on actual speech
        lengths. We iterate 

        Args:
            subs (list[srt.Subtitle]): List of subtitle objects containing text
                to synthesize.
            output_file (str, optional): Path to save the combined audio file.
                Defaults to "temp/de_audio.wav".
            speed (float, optional): Playback speed factor for synthesized speech.
                Defaults to 1.0.

        Returns:
            tuple[str, list[srt.Subtitle]]:
                - Path to the generated audio file (WAV format).
                - List of updated `srt.Subtitle` objects with adjusted start/end
                  timestamps.
        """
        full_audio = AudioSegment.silent(duration=0)
        current_time_ms = 0
        new_subs = []

        for i, sub in tqdm(enumerate(subs), total=len(subs), desc="Generating audio from subtitles"):
            # Generate temporary audio file
            temp_path = f"temp_{i}.wav"

            # We find hallucinations can be detected by abnormally long audio
            # We also want to ensure the audio and video are synchronized
            # So, we do multiple generations, if needed to achieve this

            tries = 0 # Timeout variable
            factor = 2.0  # Initialize factor to enter the loop
            sub_speed = speed # Assist in generating proper length audio segments 
            speech_attempts = [] # In case of timeout, we take minimum

            while factor > 1: # We want audio segments that are same length as original
                self.tts.tts_to_file(
                    text=sub.content,
                    speaker="MySpeaker1",
                    language="de",
                    file_path=temp_path,
                    speed=sub_speed,
                )

                # Load generated speech
                speech = AudioSegment.from_wav(temp_path)
                os.remove(temp_path)

                # Check if generated audio is a good length
                subtitle_duration_ms = (sub.end.total_seconds() - sub.start.total_seconds()) * 1000
                factor = len(speech) / subtitle_duration_ms

                # Update loop variables
                tries += 1
                sub_speed = max(1.25, sub_speed+0.025)
                speech_attempts.append(speech)

                if tries > 15:
                    print(f"Warning: Could not generate suitable audio for subtitle {i+1} after 10 attempts.")
                    break

            speech = min(speech_attempts, key=len)

            # If speech is too short, pad with silence
            if len(speech) < subtitle_duration_ms:
                silence = AudioSegment.silent(duration=subtitle_duration_ms - len(speech))
                speech += silence

            # Append speech at the current cursor
            full_audio += speech

            # Update subtitle timings
            start = datetime.timedelta(milliseconds=current_time_ms)
            end = datetime.timedelta(milliseconds=current_time_ms + len(speech))
            new_subs.append(srt.Subtitle(index=i + 1, start=start, end=end, content=sub.content))

            # Move cursor forward
            current_time_ms += len(speech)+1

        # Export combined audio and transcript
        full_audio.export(output_file, format="wav")

        # After you build new_subs and export the audio:
        srt_path = output_file.replace(".wav", ".srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(new_subs))

        return output_file, srt_path