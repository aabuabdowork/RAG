"""Composition Root: Application entry point wiring clean architecture dependencies."""
from pathlib import Path

from src.application.use_cases.analyze_document import AnalyzeDocumentUseCase
from src.application.use_cases.embed_document import EmbedDocumentUseCase
from src.application.use_cases.extract_document import ExtractDocumentUseCase
from src.core.config import settings
from src.infrastructure.embeddings.huggingface_service import HuggingFaceEmbeddingService
from src.infrastructure.llm.openrouter_service import OpenRouterLLMService
from src.infrastructure.loaders.pypdf_loader import PyPDFDocumentLoader


def main() -> None:
    # 1. Target document path
    document_path = settings.resolve_doc_path("sample.pdf")

    # 2. Infrastructure Layer (Adapters)
    pdf_loader = PyPDFDocumentLoader()
    llm_service = OpenRouterLLMService()
    embedding_service = HuggingFaceEmbeddingService()

    # 3. Application Layer (Use Cases with Injected Dependencies)
    extract_use_case = ExtractDocumentUseCase(loader=pdf_loader)
    embed_use_case = EmbedDocumentUseCase(loader=pdf_loader, embedder=embedding_service)
    analyze_use_case = AnalyzeDocumentUseCase(loader=pdf_loader, llm=llm_service)

    # 4. Execute Document Extraction
    print("=== 1. Extracting Document Content ===")
    extracted_doc = extract_use_case.execute(document_path)
    print(f"Loaded: {Path(extracted_doc.source_path).name} ({extracted_doc.total_pages} page(s))\n")
    for page in extracted_doc.pages:
        print(f"--- Page {page.page_number} ---")
        print(page.content.strip())
        print(f"Metadata: {page.metadata}\n")

    # 5. Execute Document Embedding (Free Local Embedding Model)
    print("=== 2. Free Embedding Generation (all-MiniLM-L6-v2) ===")
    embeddings = embed_use_case.execute(document_path)
    for idx, emb in enumerate(embeddings, start=1):
        print(f"Embedding Page {idx}:")
        print(f"• Vector Dimensionality : {emb.dimensions} dimensions")
        print(f"• Sample Vector Values  : [{', '.join(f'{v:.4f}' for v in emb.vector[:6])}, ...]")
        print(f"• Total Floats Generated: {len(emb.vector)}")
        print(f"• Metadata Attached     : {emb.metadata}\n")

    # 6. Execute Document Analysis (LLM)
    print("=== 3. LLM Analysis ===")
    analysis = analyze_use_case.execute(
        file_path=document_path,
        prompt_instruction="Briefly summarize what this document is about in one sentence:",
    )
    print("Summary:")
    print(analysis.strip())


if __name__ == "__main__":
    main()
