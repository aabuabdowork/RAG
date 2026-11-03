from pathlib import Path
from typing import Dict, Union

from src.application.use_cases.ingest_document import IngestDocumentUseCase


class IngestFolderUseCase:
    def __init__(self, ingest: IngestDocumentUseCase, pattern: str = "*.pdf") -> None:
        self._ingest = ingest
        self._pattern = pattern

    def execute(self, folder: Union[str, Path]) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for path in sorted(Path(folder).glob(self._pattern)):
            try:
                results[path.name] = self._ingest.execute(path)
            except Exception as error:
                results[path.name] = f"failed ({error})"
        return results
