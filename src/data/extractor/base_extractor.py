from abc import abstractmethod
from pathlib import Path
from abstract import ABC    

class BaseExtractor(ABC):

    def __init__(self, source: str | Path):
        self.source = Path(source)
        if not self.source.exists():
            raise FileNotFoundError(f"Le fichier {self.source} n'existe pas.")

    @abstractmethod
    def extract_csv(self, **kwargs):
        """Méthode à implémenter pour lire un fichier CSV."""
        pass
