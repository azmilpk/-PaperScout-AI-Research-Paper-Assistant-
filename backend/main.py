import os
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_service import RAGPipeline, SAMPLE_DOC_PATH

app = FastAPI(title="DocuMind RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=2, ge=1, le=5)


@app.get("/health")
def health():
    return {"status": "ok", "service": "documind-rag"}


@app.get("/status")
def status():
    return rag.get_status()


@app.post("/index/sample")
def index_sample():
    try:
        result = rag.index_sample_document()
        return {"message": "Sample document indexed successfully.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported for now.")

    content = await file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="wb") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = rag.index_text_file(tmp_path, source_name=file.filename)
        return {"message": f"Indexed {file.filename} successfully.", **result}
    finally:
        os.unlink(tmp_path)


@app.post("/chat")
def chat(request: ChatRequest):
    if not rag.is_indexed():
        if os.path.exists(SAMPLE_DOC_PATH):
            rag.index_sample_document()
        else:
            raise HTTPException(
                status_code=400,
                detail="No documents indexed. Upload a .txt file or index the sample document first.",
            )

    try:
        return rag.ask(request.query, top_k=request.top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
