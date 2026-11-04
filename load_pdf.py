"""Script for extracting document content via ExtractDocumentUseCase."""
from pathlib import Path

from src.application.use_cases.extract_document import ExtractDocumentUseCase
from src.core.config import settings
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader


def main() -> None:
    doc_path = settings.docs_dir / "IT" / "sample.pdf"
    loader = PyPDFDocumentLoader()
    use_case = ExtractDocumentUseCase(loader=loader)

    document = use_case.execute(doc_path)
    print(f"Extracted {document.total_pages} page(s) from {Path(document.source_path).name}:\n")
    for page in document.pages:
        print(f"--- Page {page.page_number} ---")
        print(page.content)
        print("Metadata:", page.metadata)


if __name__ == "__main__":
    main()
