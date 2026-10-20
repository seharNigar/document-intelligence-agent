from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.chunking_service import create_chunks
from app.services.document_service import (
    analyze_document_layout,
    analyze_general_document,
    analyze_invoice
)

from app.services.content_understanding_service import (
    analyze_invoice_with_content_understanding
)

from app.models.invoice import ProcessedInvoice
from app.database import initialize_database

app = FastAPI(
    title="Document Intelligence Agent",
    description="AI-powered document analysis API",
    version="1.0.0"
)

import json
import uuid

from app.services.search_service import (
    list_indexed_documents,
    upload_document
)
from app.services.foundry_agent_service import ask_foundry_agent

web_directory = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=web_directory), name="static")


@app.get("/")
def root():
    return FileResponse(web_directory / "index.html")


@app.post("/api/documents/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        return analyze_invoice(file_bytes)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/api/documents")
def get_indexed_documents():
    try:
        return {"documents": list_indexed_documents()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/documents/layout")
async def analyze_layout(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        return analyze_document_layout(file_bytes)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/documents/general")
async def analyze_general_document_endpoint(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        return analyze_general_document(file_bytes)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

@app.post(
    "/api/documents/analyze-foundry",
    response_model=ProcessedInvoice
)
async def analyze_invoice_foundry(file: UploadFile = File(...)):

    try:
        file_bytes = await file.read()

        # 1. Analyze the actual invoice
        result = analyze_invoice_with_content_understanding(
            file_bytes
        )

        # 2. Validate the structured invoice result
        processed_invoice = ProcessedInvoice.model_validate(result)

        # 3. Convert the structured result to searchable text
        invoice_content = json.dumps(
            processed_invoice.model_dump(),
            indent=2,
            default=str
        )
        document_id = str(uuid.uuid4())
        chunks = create_chunks(invoice_content)

        for index, chunk in enumerate(chunks):

            chunk_id = f"{uuid.uuid4()}-{index}"

            upload_document(
                document_id=chunk_id,
                document_name=file.filename,
                content=chunk,
                document_type="invoice",
                page_number=1,
                metadata=json.dumps({
                    "source": "content-understanding",
                    "original_filename": file.filename,
                    "document_id": document_id,
                    "chunk_index": index
                })
            )

        # 6. Return the extracted invoice as before
        return processed_invoice

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

class QuestionRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    document_name: str | None = None


@app.on_event("startup")
def startup():
    initialize_database()


@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    try:
        result = ask_foundry_agent(
            request.question,
            request.conversation_id,
            request.document_name
        )
        result["document_name"] = request.document_name
        return result
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))