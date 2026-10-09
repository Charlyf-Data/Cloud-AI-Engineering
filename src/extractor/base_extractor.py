from pathlib import Path

class BaseExtractor():
    """Contrat abstrait pour tous les extracteurs de données."""

    def __init__(self, source: str | Path):
        self.source = Path(source)
        if not self.source.exists():
            raise FileNotFoundError(f"Le fichier {self.source} n'existe pas.")

    def extract_csv(self, **kwargs):
        """Méthode à implémenter pour lire un fichier CSV."""
        pass
