from fastapi import APIRouter, UploadFile, File, HTTPException
from core.rag.knowledge_base import kb
from commons.logger import logger
import os
import shutil

log = logger(__name__)
router = APIRouter()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF or Text file to the Knowledge Base.
    """
    try:
        log.info(f"Received file upload: {file.filename}")

        # Save file temporarily
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Add to Knowledge Base
        kb.add_document(file_path)

        return {
            "message": "Document uploaded and indexed successfully",
            "filename": file.filename,
        }
    except Exception as e:
        log.error(f"Failed to process upload: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process document: {str(e)}"
        )
