from pathlib import Path
from typing import Dict, Union

from src.application.use_cases.ingest_document import IngestDocumentUseCase


class IngestFolderUseCase:
    def __init__(self, ingest: IngestDocumentUseCase, pattern: str = "*.pdf") -> None:
        self._ingest = ingest
        self._pattern = pattern

    def execute(self, folder: Union[str, Path]) -> Dict[str, str]:
        root = Path(folder)
        results: Dict[str, str] = {}
        for department_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for path in sorted(department_dir.rglob(self._pattern)):
                key = f"{department_dir.name}/{path.name}"
                try:
                    results[key] = self._ingest.execute(path, department=department_dir.name)
                except Exception as error:
                    results[key] = f"failed ({error})"
        return results
