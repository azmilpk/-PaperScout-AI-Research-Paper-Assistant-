import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pypdf
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# Base paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db_store")
DATA_DIR = os.path.join(BACKEND_DIR, "data")
PAPERS_REGISTRY_PATH = os.path.join(DATA_DIR, "papers_registry.json")
SAMPLE_PAPER_PATH = os.path.join(DATA_DIR, "sample_papers", "attention_is_all_you_need.txt")
COLLECTION_NAME = "paperscout_papers_store"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "sample_papers"), exist_ok=True)

# Load environment variables
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)


class LocalDefaultEmbeddings(Embeddings):
    """
    Fast, local, zero-quota embedding function powered by ONNX / all-MiniLM-L6-v2.
    Ensures vector indexing and retrieval work smoothly without consuming LLM API quotas.
    """
    def __init__(self):
        self._ef = embedding_functions.DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._ef(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._ef([text])[0]


def get_embedding_function() -> Embeddings:
    """Return the selected LangChain Embeddings instance."""
    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower().strip()
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if provider == "google" and google_key:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_key,
        )

    if provider == "openai" and openai_key:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_key,
        )

    return LocalDefaultEmbeddings()


def get_configured_llm():
    """
    Resolve real LLM model based on environment variables.
    Strictly requires a real API key - supports Hugging Face, Gemini, or OpenAI.
    """
    load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if hf_token:
        from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
        model_name = os.getenv("HUGGINGFACE_MODEL", "microsoft/Phi-3-mini-4k-instruct")
        endpoint = HuggingFaceEndpoint(
            repo_id=model_name,
            task="text-generation",
            huggingfacehub_api_token=hf_token,
            temperature=0.1,
            max_new_tokens=600,
        )
        llm = ChatHuggingFace(llm=endpoint)
        return llm, "huggingface", model_name

    if google_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_key,
            temperature=0.1,
        )
        return llm, "google", model_name

    if openai_key:
        from langchain_openai import ChatOpenAI
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=openai_key,
            temperature=0.1,
        )
        return llm, "openai", model_name

    raise RuntimeError(
        "No LLM API key configured. Please configure HUGGINGFACEHUB_API_TOKEN, "
        "GOOGLE_API_KEY, or OPENAI_API_KEY in your .env file or via the topbar settings."
    )


def slugify(text: str) -> str:
    """Generate a clean slug for paper IDs."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:40]


class PaperScoutRAGPipeline:
    def __init__(self, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_function = get_embedding_function()
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=750,
            chunk_overlap=120,
            separators=["\n\nSECTION ", "\n## ", "\n# ", "\n\n", "\n", " ", ""],
        )

    # -------------------------------------------------------------------------
    # Registry Management (My Papers)
    # -------------------------------------------------------------------------
    def _read_registry(self) -> List[dict]:
        if not os.path.exists(PAPERS_REGISTRY_PATH):
            return []
        try:
            with open(PAPERS_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write_registry(self, papers: List[dict]):
        with open(PAPERS_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2)

    def list_papers(self) -> List[dict]:
        """Return all tracked research papers."""
        return self._read_registry()

    def get_paper(self, paper_id: str) -> Optional[dict]:
        for p in self._read_registry():
            if p["id"] == paper_id:
                return p
        return None

    def delete_paper(self, paper_id: str) -> bool:
        """Delete paper chunks from Chroma and remove from registry."""
        try:
            # Delete chunks in Chroma matching paper_id
            col = self.chroma_client.get_collection(self.collection_name)
            col.delete(where={"paper_id": paper_id})
        except Exception:
            pass

        papers = [p for p in self._read_registry() if p["id"] != paper_id]
        self._write_registry(papers)
        return True

    # -------------------------------------------------------------------------
    # Status & Health
    # -------------------------------------------------------------------------
    def is_indexed(self) -> bool:
        try:
            col = self.chroma_client.get_collection(self.collection_name)
            return col.count() > 0
        except Exception:
            return False

    def get_status(self) -> dict:
        indexed = self.is_indexed()
        chunk_count = 0
        if indexed:
            try:
                col = self.chroma_client.get_collection(self.collection_name)
                chunk_count = col.count()
            except Exception:
                pass

        papers = self.list_papers()

        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
        google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        key_configured = bool(hf_token or google_key or openai_key)

        if hf_token:
            provider = "huggingface"
            model = os.getenv("HUGGINGFACE_MODEL", "microsoft/Phi-3-mini-4k-instruct")
        elif google_key:
            provider = "google"
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        elif openai_key:
            provider = "openai"
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        else:
            provider = "none"
            model = "none"

        return {
            "app_name": "PaperScout",
            "indexed": indexed,
            "collection": self.collection_name,
            "chunk_count": chunk_count,
            "papers_count": len(papers),
            "sample_paper_available": os.path.exists(SAMPLE_PAPER_PATH),
            "key_configured": key_configured,
            "llm_provider": provider,
            "llm_model": model,
        }

    # -------------------------------------------------------------------------
    # Document Parsing & Ingestion (Phase 1)
    # -------------------------------------------------------------------------
    def _extract_pdf_pages(self, file_path: str, filename: str) -> Tuple[List[Document], str, str]:
        """Extract pages from PDF, infer title and abstract."""
        reader = pypdf.PdfReader(file_path)
        docs = []
        full_text = ""

        for idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                full_text += f"\n{page_text}"
                docs.append(Document(
                    page_content=page_text,
                    metadata={"page": idx + 1, "filename": filename},
                ))

        if not docs:
            raise ValueError("Could not extract any readable text from the uploaded PDF.")

        # Heuristic title detection from first page
        first_lines = [l.strip() for l in docs[0].page_content.split("\n") if l.strip()][:5]
        title = first_lines[0] if first_lines else os.path.splitext(filename)[0]
        if len(title) > 90:
            title = os.path.splitext(filename)[0]

        # Extract abstract preview
        abstract = ""
        match = re.search(r"ABSTRACT[\s:]*(.+?)(?=\n[0-9]+\.?\s+[A-Z]|\nSECTION|\n1\s+Introduction)", full_text, re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()[:300] + "..."
        else:
            abstract = docs[0].page_content[:250].strip() + "..."

        return docs, title, abstract

    def _extract_text_pages(self, content: str, filename: str) -> Tuple[List[Document], str, str]:
        """Extract pages and sections from text or markdown."""
        # Check for [PAGE X] markers
        page_splits = re.split(r"(?=\[PAGE\s+\d+\])", content)
        docs = []

        if len(page_splits) > 1:
            for idx, part in enumerate(page_splits):
                part_s = part.strip()
                if not part_s:
                    continue
                # Extract page number if present
                m = re.match(r"\[PAGE\s+(\d+)\]", part_s)
                page_num = int(m.group(1)) if m else (idx + 1)
                clean_text = re.sub(r"\[PAGE\s+\d+\]", "", part_s).strip()
                docs.append(Document(
                    page_content=clean_text,
                    metadata={"page": page_num, "filename": filename},
                ))
        else:
            docs.append(Document(
                page_content=content.strip(),
                metadata={"page": 1, "filename": filename},
            ))

        # Title heuristic
        title_match = re.search(r"PAPER TITLE:\s*(.+)", content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            first_line = content.strip().split("\n")[0].replace("#", "").strip()
            title = first_line if len(first_line) < 80 else os.path.splitext(filename)[0]

        # Abstract heuristic
        abstract_match = re.search(r"ABSTRACT[\s:]*(.+?)(?=\n(?:SECTION|\d+\.|\n\n))", content, re.DOTALL | re.IGNORECASE)
        abstract = abstract_match.group(1).strip()[:300] + "..." if abstract_match else docs[0].page_content[:250].strip() + "..."

        return docs, title, abstract

    def index_paper_file(self, file_path: str, filename: str) -> dict:
        """
        Ingest, parse, chunk, and index a research paper into ChromaDB.
        Adds paper metadata into the registry.
        """
        paper_id = slugify(os.path.splitext(filename)[0])
        # Check actual file path extension as well as uploaded filename
        is_pdf = file_path.lower().endswith(".pdf") or (filename.lower().endswith(".pdf") and not file_path.lower().endswith(".txt"))

        if is_pdf:
            page_docs, title, abstract = self._extract_pdf_pages(file_path, filename)
        else:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            page_docs, title, abstract = self._extract_text_pages(content, filename)

        # Split each page into granular chunks with section detection
        all_chunks = []
        for p_doc in page_docs:
            page_num = p_doc.metadata.get("page", 1)
            raw_chunks = self.text_splitter.split_text(p_doc.page_content)

            for i, chunk_text in enumerate(raw_chunks):
                # Detect section header in this chunk
                section_title = f"Page {page_num}"
                lines = [l.strip() for l in chunk_text.split("\n") if l.strip()]
                for l in lines[:3]:
                    if re.match(r"^(SECTION\s+\d+|[0-9]+\.[0-9]*\s+[A-Z]|ABSTRACT|CONCLUSION|INTRODUCTION|BACKGROUND)", l, re.IGNORECASE):
                        section_title = l.replace("#", "").strip()
                        break

                all_chunks.append(Document(
                    page_content=chunk_text,
                    metadata={
                        "paper_id": paper_id,
                        "paper_title": title,
                        "filename": filename,
                        "page": page_num,
                        "section": section_title,
                        "chunk_id": len(all_chunks),
                    },
                ))

        # Delete any previous chunks for this paper_id before adding
        try:
            col = self.chroma_client.get_collection(self.collection_name)
            col.delete(where={"paper_id": paper_id})
        except Exception:
            pass

        # Add new chunks to ChromaDB
        self.vector_store.add_documents(all_chunks)

        # Update registry
        paper_info = {
            "id": paper_id,
            "filename": filename,
            "title": title,
            "total_pages": len(page_docs),
            "chunk_count": len(all_chunks),
            "abstract": abstract,
            "uploaded_at": datetime.now().isoformat(),
        }

        existing_papers = [p for p in self._read_registry() if p["id"] != paper_id]
        existing_papers.insert(0, paper_info)
        self._write_registry(existing_papers)

        return {
            "message": f"Successfully indexed '{title}' ({len(page_docs)} pages, {len(all_chunks)} chunks).",
            "paper": paper_info,
        }

    def index_sample_paper(self) -> dict:
        """Load and index the bundled 'Attention Is All You Need' foundational paper."""
        if not os.path.exists(SAMPLE_PAPER_PATH):
            raise FileNotFoundError("Sample research paper not found.")
        return self.index_paper_file(SAMPLE_PAPER_PATH, filename="Attention Is All You Need.pdf")

    # -------------------------------------------------------------------------
    # Retrieval & Q&A with Strict Citations
    # -------------------------------------------------------------------------
    def retrieve_context(self, query: str, paper_id: Optional[str] = None, top_k: int = 4) -> List[Tuple[Document, float]]:
        """
        Retrieve top-k chunks from ChromaDB.
        Supports filtering by specific paper_id or searching across all uploaded papers.
        """
        if not self.is_indexed():
            raise RuntimeError("No research papers indexed. Please upload a paper or index the sample paper first.")

        filter_kwargs = {"paper_id": paper_id} if paper_id else None
        return self.vector_store.similarity_search_with_score(query, k=top_k, filter=filter_kwargs)

    def is_greeting(self, text: str) -> bool:
        """Intent classifier for basic chitchat/greetings to prevent hallucination."""
        clean = text.strip().lower()
        greetings = {
            "hi", "hai", "hello", "hey", "good morning", "good evening",
            "how are you", "who are you", "what can you do", "help"
        }
        return clean in greetings or any(clean.startswith(g + " ") for g in ["hi", "hello", "hey"])

    def ask(self, query: str, paper_id: Optional[str] = None, top_k: int = 4) -> dict:
        """
        End-to-End Grounded Paper Q&A with Query Routing and Exact Citations.
        """
        # Step 1: Query Router - Handle greetings without hallucinating
        if self.is_greeting(query):
            active_paper = self.get_paper(paper_id) if paper_id else None
            paper_context_str = f" Currently viewing '{active_paper['title']}'." if active_paper else " You have multiple papers loaded in your library."
            return {
                "query": query,
                "answer": (
                    f"Hello! I am **PaperScout**, your Research Paper Assistant.{paper_context_str}\n\n"
                    "Ask me anything about model architectures, equations, experimental benchmarks, or comparisons!"
                ),
                "citations": [],
                "grounded": True,
                "is_greeting": True,
            }

        # Step 2: Retrieve relevant passages with similarity scores
        docs_and_scores = self.retrieve_context(query, paper_id=paper_id, top_k=top_k)
        if not docs_and_scores:
            raise RuntimeError("No matching passages found in the selected paper.")

        # Step 3: Format Context & Citations
        context_parts = []
        citations = []
        for idx, (doc, score) in enumerate(docs_and_scores, 1):
            paper_title = doc.metadata.get("paper_title", "Research Paper")
            page_num = doc.metadata.get("page", 1)
            section = doc.metadata.get("section", f"Page {page_num}")
            cite_label = f"[{idx}] {paper_title} (Page {page_num}, {section})"

            context_parts.append(f"--- SOURCE {cite_label} ---\n{doc.page_content}")
            citations.append({
                "citation_id": idx,
                "paper_id": doc.metadata.get("paper_id"),
                "paper_title": paper_title,
                "section": section,
                "page": page_num,
                "source": doc.metadata.get("filename", "Paper"),
                "distance": round(float(score), 4),
                "text": doc.page_content,
            })

        formatted_context = "\n\n".join(context_parts)

        # Step 4: Resolve real LLM
        llm, provider, model_name = get_configured_llm()

        # Step 5: Grounded Prompt Template
        rag_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are PaperScout, an elite AI Research Paper Assistant.\n"
                "Your objective is to provide deep, accurate, and mathematically precise explanations based EXCLUSIVELY on the provided research context.\n"
                "Strict Guidelines:\n"
                "1. Base your answer ONLY on the provided context passages. Never fabricate details, equations, or author claims.\n"
                "2. If the context does not contain the answer, explicitly state: 'The provided paper context does not mention this information.'\n"
                "3. Use in-text citation markers like [1], [2] corresponding to the numbered context sources whenever making a claim.\n"
                "4. Where applicable, provide clear architectural explanations, bullet points, or formulas.\n"
                "5. End your answer with a 'Sources:' list referencing the citations."
            ),
            (
                "human",
                "==================================================\n"
                "RESEARCH PAPER PASSAGES:\n"
                "==================================================\n"
                "{context}\n\n"
                "==================================================\n"
                "USER QUESTION:\n"
                "{query}\n"
                "==================================================\n\n"
                "Please explain thoroughly with source citations:"
            ),
        ])

        # Step 6: Execute LangChain LCEL pipeline
        rag_chain = rag_prompt | llm | StrOutputParser()
        answer = rag_chain.invoke({
            "context": formatted_context,
            "query": query,
        })

        return {
            "query": query,
            "answer": answer,
            "citations": citations,
            "grounded": True,
            "llm_provider": provider,
            "llm_model": model_name,
            "paper_id": paper_id,
        }
