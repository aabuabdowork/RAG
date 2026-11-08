from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile

from src.api.dependencies import ContainerDep, limiter
from src.api.schemas import DocumentOut, UploadResponse, check_department
from src.application.use_cases.upload_document import document_id
from src.core.config import settings
from src.domain.entities import DocumentStatus

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_BYTES = settings.max_upload_mb * 1024 * 1024


def parse_department(value: str) -> str:
    try:
        return check_department(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("", status_code=202, response_model=UploadResponse)
@limiter.limit(settings.rate_limit_write)
def upload(
    request: Request,
    background: BackgroundTasks,
    container: ContainerDep,
    department: str = Form(...),
    file: UploadFile = File(...),
) -> UploadResponse:
    department = parse_department(department)
    file_name = Path(file.filename or "").name
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only .pdf files are accepted")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File is larger than {settings.max_upload_mb} MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="File content is not a PDF")

    result = container.upload().execute(file_name, data, department)
    if result != "skipped":
        background.add_task(container.index_pending)
    return UploadResponse(id=document_id(department, file_name), document=f"{department}/{file_name}", result=result)


@router.get("", response_model=List[DocumentOut])
@limiter.limit(settings.rate_limit_read)
def list_documents(
    request: Request, container: ContainerDep, status: Optional[DocumentStatus] = None
) -> List[DocumentOut]:
    return [DocumentOut.of(document) for document in container.repository.list(status)]


@router.get("/{department}/{file_name}", response_model=DocumentOut)
@limiter.limit(settings.rate_limit_read)
def get_document(request: Request, department: str, file_name: str, container: ContainerDep) -> DocumentOut:
    document = container.repository.get(parse_department(department), file_name)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.of(document)


@router.delete("/{department}/{file_name}")
@limiter.limit(settings.rate_limit_write)
def delete_document(request: Request, department: str, file_name: str, container: ContainerDep) -> Dict[str, str]:
    result = container.delete().execute(parse_department(department), file_name)
    if result == "not found":
        raise HTTPException(status_code=404, detail="Document not found")
    return {"result": result}


@router.post("/reconcile")
@limiter.limit(settings.rate_limit_write)
def reconcile(request: Request, background: BackgroundTasks, container: ContainerDep) -> Dict[str, str]:
    results = container.reconcile().execute()
    background.add_task(container.index_pending)
    return results
