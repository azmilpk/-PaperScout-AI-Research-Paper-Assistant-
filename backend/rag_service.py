import os
import chromadb
from chromadb.utils import embedding_functions

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db_store")
SAMPLE_DOC_PATH = os.path.join(PROJECT_ROOT, "learning", "sample_company_policy.txt")
COLLECTION_NAME = "acme_company_policy"


def chunk_document(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = content.split("SECTION ")
    chunks = []

    for idx, sec in enumerate(sections):
        sec = sec.strip()
        if not sec:
            continue

        lines = sec.split("\n", 1)
        section_title = f"SECTION {lines[0].strip()}"
        body = lines[1].strip() if len(lines) > 1 else lines[0].strip()

        chunks.append({
            "id": f"chunk_{idx}",
            "text": f"{section_title}\n{body}",
            "metadata": {
                "section": section_title,
                "chunk_id": idx,
                "source": os.path.basename(file_path),
            },
        })

    return chunks


class RAGPipeline:
    def __init__(self, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME):
        self.db_path = db_path
        self.collection_name = collection_name
        self.default_ef = embedding_functions.DefaultEmbeddingFunction()
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = None
        self._load_collection()

    def _load_collection(self):
        try:
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=self.default_ef,
            )
        except Exception:
            self.collection = None

    def is_indexed(self) -> bool:
        return self.collection is not None and self.collection.count() > 0

    def get_status(self) -> dict:
        if not self.is_indexed():
            return {
                "indexed": False,
                "collection": self.collection_name,
                "chunk_count": 0,
                "sample_doc_available": os.path.exists(SAMPLE_DOC_PATH),
            }
        return {
            "indexed": True,
            "collection": self.collection_name,
            "chunk_count": self.collection.count(),
            "sample_doc_available": os.path.exists(SAMPLE_DOC_PATH),
        }

    def index_sample_document(self) -> dict:
        if not os.path.exists(SAMPLE_DOC_PATH):
            raise FileNotFoundError("Sample company policy document not found.")

        chunks = chunk_document(SAMPLE_DOC_PATH)

        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            embedding_function=self.default_ef,
            metadata={"description": "Acme Corp Policy Documents Vector Index"},
        )

        self.collection.add(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks],
        )

        return {"indexed_chunks": len(chunks), "collection": self.collection_name}

    def index_text_file(self, file_path: str, source_name: str) -> dict:
        chunks = chunk_document(file_path)

        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            embedding_function=self.default_ef,
            metadata={"description": f"Indexed from {source_name}"},
        )

        for chunk in chunks:
            chunk["metadata"]["source"] = source_name

        self.collection.add(
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
            ids=[c["id"] for c in chunks],
        )

        return {"indexed_chunks": len(chunks), "collection": self.collection_name}

    def retrieve_context(self, query: str, top_k: int = 2) -> list[dict]:
        if not self.is_indexed():
            raise RuntimeError("No documents indexed. Run step 2 or index via the API first.")

        results = self.collection.query(query_texts=[query], n_results=top_k)

        retrieved_chunks = []
        for i in range(len(results["documents"][0])):
            retrieved_chunks.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })

        return retrieved_chunks

    def build_grounded_prompt(self, query: str, chunks: list) -> str:
        context_str = "\n\n".join([
            f"--- CONTEXT PASSAGE [{c['metadata']['section']}] ---\n{c['text']}"
            for c in chunks
        ])

        return f"""You are an Enterprise HR & Policy Assistant for Acme Corp.
Answer the user's question accurately using ONLY the provided document context below.
If the answer cannot be found in the context, explicitly state "I cannot find this information in the official policy documents."
Always include citations to the specific section name.

==================================================
DOCUMENT CONTEXT:
==================================================
{context_str}

==================================================
USER QUESTION:
{query}
==================================================

ANSWER WITH CITATIONS:"""

    def generate_answer(self, prompt: str, chunks: list) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")

        if api_key:
            try:
                from google import genai

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                return response.text
            except Exception:
                pass

        citation = chunks[0]["metadata"]["section"]
        passage_summary = chunks[0]["text"].split("\n", 1)[-1].strip()

        return (
            f"Based on official policy [{citation}], {passage_summary}\n\n"
            f"[Source Citation: {citation}]"
        )

    def ask(self, query: str, top_k: int = 2) -> dict:
        chunks = self.retrieve_context(query, top_k=top_k)
        prompt = self.build_grounded_prompt(query, chunks)
        answer = self.generate_answer(prompt, chunks)

        return {
            "query": query,
            "answer": answer,
            "citations": [
                {
                    "section": c["metadata"]["section"],
                    "source": c["metadata"].get("source", "unknown"),
                    "distance": c["distance"],
                    "text": c["text"],
                }
                for c in chunks
            ],
            "grounded": True,
        }
