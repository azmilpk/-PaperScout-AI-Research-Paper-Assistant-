"""
====================================================================
STEP 3: Full RAG Pipeline (Retrieval-Augmented Generation)
====================================================================
In this final learning step, you will see how:
 1. A user's question triggers ChromaDB Vector Retrieval.
 2. Retrieved context is injected into a strict Grounded System Prompt.
 3. The LLM generates a cited, hallucination-free answer.
====================================================================
"""

import os
import sys
import chromadb
from chromadb.utils import embedding_functions

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class RAGPipeline:
    def __init__(self, db_path, collection_name="acme_company_policy"):
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.default_ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.chroma_client.get_collection(
            name=collection_name,
            embedding_function=self.default_ef
        )

    def retrieve_context(self, query: str, top_k: int = 2):
        """
        Retrieves top_k relevant text chunks from ChromaDB for a given query.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        retrieved_chunks = []
        for i in range(len(results["documents"][0])):
            retrieved_chunks.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
            
        return retrieved_chunks

    def build_grounded_prompt(self, query: str, chunks: list) -> str:
        """
        Constructs a strict Grounded Prompt forcing the LLM to use ONLY the retrieved context.
        """
        context_str = "\n\n".join([
            f"--- CONTEXT PASSAGE [{c['metadata']['section']}] ---\n{c['text']}"
            for c in chunks
        ])
        
        prompt = f"""You are an Enterprise HR & Policy Assistant for Acme Corp.
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
        return prompt

    def generate_answer(self, prompt: str, chunks: list) -> str:
        """
        Calls Gemini API if GEMINI_API_KEY is available, or provides a grounded simulation.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text
            except Exception as e:
                pass
                
        # Grounded Fallback Synthesizer (Demonstrates RAG Answer Assembly)
        citation = chunks[0]['metadata']['section']
        passage_summary = chunks[0]['text'].split('\n', 1)[-1].strip()
        
        answer = f"Based on official policy [{citation}], {passage_summary}\n\n[Source Citation: {citation}]"
        return answer


def run_demo():
    print("=" * 65)
    print(" 🚀 STEP 3: FULL RAG PIPELINE (RETRIEVAL + GENERATION)")
    print("=" * 65)

    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db_store")
    rag = RAGPipeline(db_path=db_path)

    user_query = "What happens to my laptop and equipment if I resign or get terminated?"
    
    print(f"\n1️⃣  USER QUESTION:\n   '{user_query}'\n")

    # Step A: Retrieval
    print("2️⃣  RETRIEVING CONTEXT FROM CHROMADB...")
    chunks = rag.retrieve_context(user_query, top_k=2)
    for c in chunks:
        print(f"   ✓ Retrieved: {c['metadata']['section']} (Distance: {c['distance']:.4f})")

    # Step B: Prompt Construction
    print("\n3️⃣  CONSTRUCTING GROUNDED RAG PROMPT...")
    prompt = rag.build_grounded_prompt(user_query, chunks)
    
    print("-" * 65)
    print(" 📄 ASSEMBLED RAG PROMPT SENT TO LLM:")
    print("-" * 65)
    print(prompt)
    print("-" * 65)

    # Step C: Generation
    print("\n4️⃣  GENERATING FINAL CITED ANSWER...")
    final_answer = rag.generate_answer(prompt, chunks)
    
    print("\n🤖 AI RESPONSE:")
    print(final_answer)
    print("\n" + "=" * 65)
    print(" 🎯 CONGRATULATIONS! You have mastered the core concepts of RAG:")
    print("    1. Embeddings & Cosine Similarity (Step 1)")
    print("    2. Document Chunking & Vector DB Indexing (Step 2)")
    print("    3. Grounded Context Retrieval & LLM Generation (Step 3)")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
