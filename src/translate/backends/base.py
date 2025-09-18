from abc import ABC, abstractmethod

class Translator(ABC):
    """
    Abstract base class for transcript translation models.
    """

    @abstractmethod
    def translate(self, text: str) -> str:
        """
        Translate input text and return translated text.
        """
        pass