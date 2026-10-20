import os
import tempfile
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag_service import (
    PaperScoutRAGPipeline,
    SAMPLE_PAPER_PATH,
    BACKEND_DIR,
    PROJECT_ROOT,
)

app = FastAPI(
    title="PaperScout Research Assistant API",
    description="Full-stack AI Research Paper Assistant powered by LangChain, ChromaDB, and real LLMs",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = PaperScoutRAGPipeline()


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    paper_id: Optional[str] = None
    top_k: int = Field(default=4, ge=1, le=10)


class ApiKeyConfigRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|openai|huggingface)$")
    api_key: str = Field(..., min_length=5)
    model: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "PaperScout", "engine": "LangChain"}


@app.get("/status")
def status():
    return rag.get_status()


# -----------------------------------------------------------------------------
# Paper Management Endpoints (Phase 1)
# -----------------------------------------------------------------------------
@app.get("/papers")
def list_papers():
    """List all uploaded research papers in the user's library."""
    papers = rag.list_papers()
    return {"papers": papers, "total": len(papers)}


@app.get("/papers/{paper_id}")
def get_paper(paper_id: str):
    paper = rag.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found.")
    return paper


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: str):
    success = rag.delete_paper(paper_id)
    return {"message": f"Paper '{paper_id}' removed from library.", "success": success}


@app.post("/papers/sample")
def index_sample_paper():
    """Load the bundled 'Attention Is All You Need' foundational paper."""
    try:
        result = rag.index_sample_paper()
        return {"message": "Sample paper loaded successfully.", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load sample paper: {str(exc)}") from exc


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a research paper (.pdf, .txt, .md)."""
    filename = file.filename or ""
    allowed_exts = (".pdf", ".txt", ".md")
    if not any(filename.lower().endswith(ext) for ext in allowed_exts):
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Please upload a research paper (.pdf, .txt, or .md).",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, mode="wb") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = rag.index_paper_file(tmp_path, filename=filename)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to index paper: {str(exc)}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# -----------------------------------------------------------------------------
# Q&A / Chat Endpoint
# -----------------------------------------------------------------------------
@app.post("/chat")
def chat(request: ChatRequest):
    # Auto-load sample paper if vector DB is completely empty and sample exists
    if not rag.is_indexed():
        if os.path.exists(SAMPLE_PAPER_PATH):
            rag.index_sample_paper()
        else:
            raise HTTPException(
                status_code=400,
                detail="No research papers indexed. Upload a research paper (.pdf, .txt, .md) to start.",
            )

    try:
        return rag.ask(request.query, paper_id=request.paper_id, top_k=request.top_k)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PaperScout analysis error: {str(exc)}") from exc


# -----------------------------------------------------------------------------
# LLM Key Settings Endpoints
# -----------------------------------------------------------------------------
@app.get("/settings/api-key")
def get_key_status():
    st = rag.get_status()
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    masked = ""
    active_key = hf_token or google_key or openai_key
    if active_key and len(active_key) > 8:
        masked = active_key[:4] + "..." + active_key[-4:]
    elif active_key:
        masked = "****"

    return {
        "key_configured": st["key_configured"],
        "llm_provider": st["llm_provider"],
        "llm_model": st["llm_model"],
        "masked_key": masked,
    }


@app.post("/settings/api-key")
def configure_api_key(req: ApiKeyConfigRequest):
    key = req.api_key.strip()
    provider = req.provider.lower().strip()
    env_path = os.path.join(BACKEND_DIR, ".env")

    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    key_map = {}
    for line in env_lines:
        line_s = line.strip()
        if "=" in line_s and not line_s.startswith("#"):
            k, v = line_s.split("=", 1)
            key_map[k.strip()] = v.strip()

    if provider == "huggingface":
        key_map["HUGGINGFACEHUB_API_TOKEN"] = key
        key_map["HF_TOKEN"] = key
        if req.model:
            key_map["HUGGINGFACE_MODEL"] = req.model.strip()
        elif "HUGGINGFACE_MODEL" not in key_map:
            key_map["HUGGINGFACE_MODEL"] = "mistralai/Mistral-7B-Instruct-v0.3"
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = key
        os.environ["HF_TOKEN"] = key
    elif provider == "google":
        key_map["GOOGLE_API_KEY"] = key
        key_map["GEMINI_API_KEY"] = key
        if req.model:
            key_map["GEMINI_MODEL"] = req.model.strip()
        elif "GEMINI_MODEL" not in key_map:
            key_map["GEMINI_MODEL"] = "gemini-2.5-flash"
        os.environ["GOOGLE_API_KEY"] = key
        os.environ["GEMINI_API_KEY"] = key
    elif provider == "openai":
        key_map["OPENAI_API_KEY"] = key
        if req.model:
            key_map["OPENAI_MODEL"] = req.model.strip()
        elif "OPENAI_MODEL" not in key_map:
            key_map["OPENAI_MODEL"] = "gpt-4o-mini"
        os.environ["OPENAI_API_KEY"] = key

    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in key_map.items():
            f.write(f"{k}={v}\n")

    load_dotenv(env_path, override=True)

    target_model = key_map.get(
        "HUGGINGFACE_MODEL" if provider == "huggingface" else ("GEMINI_MODEL" if provider == "google" else "OPENAI_MODEL")
    )

    return {
        "message": f"Successfully configured {provider.capitalize()} API key.",
        "provider": provider,
        "model": target_model,
        "key_configured": True,
    }
