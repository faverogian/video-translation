from transformers import pipeline
from .base import Translator

class HelsinkiTranslator(Translator):
    """
    Pre-trained Helsinki-NLP translation model wrapper. Uses Hugging Face transformers pipeline.
    CPU/GPU compatible, but runs efficiently on CPU for more lightweight environments.
    """
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-en-de", device="cpu"):
        self.translator = pipeline("translation", model=model_name, device=device)

    def translate(self, text: str) -> str:
        return self.translator(text, max_length=512)[0]['translation_text']