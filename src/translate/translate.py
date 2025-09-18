import srt
from pathlib import Path
from typing import List
from tqdm import tqdm

from .backends.helsinki import HelsinkiTranslator

class TranscriptTranslator:
    """
    A utility class for translating subtitle files in SRT format from English
    to another language using a specified backend translator.

    Supported backends:
        - "helsinki": Uses the Hugging Face Helsinki-NLP translation models.
    """

    def __init__(self, device="cpu"):
        """
        Initialize a TranscriptTranslator on a specified device
        """
        self.translator = HelsinkiTranslator("Helsinki-NLP/opus-mt-en-de", device)

    def translate_srt(self, input_srt: str) -> List[srt.Subtitle]:
        """
        Translate the contents of an SRT subtitle file from English into German
        while preserving original subtitle timings.

        Args:
            input_srt (str): Path to the input SRT file containing English subtitles.

        Returns:
            List[srt.Subtitle]: A list of `srt.Subtitle` objects with translated text
            and unchanged timestamps.

        Raises:
            FileNotFoundError: If the provided SRT file path does not exist.
        """
        srt_path = Path(input_srt)
        if not srt_path.exists():
            raise FileNotFoundError(f"SRT file not found: {srt_path}")

        # Parse the SRT file
        with open(srt_path, "r", encoding="utf-8") as f:
            subtitles = list(srt.parse(f.read()))

        # Translate subtitle content line by line
        for sub in tqdm(subtitles, desc="Translating subtitles"):
            de_content = self.translator.translate(sub.content)
            sub.content = de_content

        return subtitles
