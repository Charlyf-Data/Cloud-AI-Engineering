
from pathlib import Path 
import polars as pl  
from .base_extractor import BaseExtractor

class PolarsExtractor(BaseExtractor):

    def __init__(self, source: str | Path):
        super().__init__(source)
        self.source = Path(source)

    def extract_csv(self, lazy: bool = True) -> pl.DataFrame | pl.LazyFrame:
        if lazy:
            return pl.scan_csv(self.source)
        return pl.read_csv(self.source)
