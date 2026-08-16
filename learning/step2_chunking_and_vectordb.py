"""
====================================================================
STEP 2: Document Chunking & ChromaDB Vector Database
====================================================================
In this script, you will learn:
 1. How raw text is divided into logical 'Chunks' with Metadata.
 2. How to store chunks into a local persistent ChromaDB collection.
 3. How to query ChromaDB for semantic vector retrieval.
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


def chunk_document(file_path):
    """
    Splits document text into logical sections/chunks with metadata.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by section headers
    sections = content.split("SECTION ")
    chunks = []
    
    for idx, sec in enumerate(sections):
        sec = sec.strip()
        if not sec:
            continue
        
        # Extract title and body
        lines = sec.split("\n", 1)
        section_title = f"SECTION {lines[0].strip()}"
        body = lines[1].strip() if len(lines) > 1 else lines[0].strip()
        
        chunks.append({
            "id": f"chunk_{idx}",
            "text": f"{section_title}\n{body}",
            "metadata": {
                "section": section_title,
                "chunk_id": idx,
                "source": os.path.basename(file_path)
            }
        })
        
    return chunks


def run_demo():
    print("=" * 65)
    print(" 🚀 STEP 2: DOCUMENT CHUNKING & CHROMADB VECTOR DATABASE")
    print("=" * 65)

    sample_doc_path = os.path.join(os.path.dirname(__file__), "sample_company_policy.txt")
    
    # 1. Chunking phase
    print("\n1️⃣  CHUNKING DOCUMENT...")
    chunks = chunk_document(sample_doc_path)
    print(f"   Successfully generated {len(chunks)} chunks from sample document.\n")
    
    for c in chunks:
        print(f"   📌 [{c['id']}] Metadata: {c['metadata']['section']}")

    # 2. Vector DB Initialization phase
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db_store")
    print(f"\n2️⃣  INITIALIZING CHROMADB AT:\n   '{db_path}'")
    
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # Using Default Embedding Function (ONNX MiniLM)
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    
    collection_name = "acme_company_policy"
    # Reset collection if exists for clean demo
    try:
        chroma_client.delete_collection(name=collection_name)
    except Exception:
        pass
        
    collection = chroma_client.create_collection(
        name=collection_name,
        embedding_function=default_ef,
        metadata={"description": "Acme Corp Policy Documents Vector Index"}
    )

    # 3. Ingestion phase (Embedding + Storing)
    print("\n3️⃣  STORING CHUNKS INTO CHROMADB...")
    collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        ids=[c["id"] for c in chunks]
    )
    print(f"   Indexed {collection.count()} chunks into ChromaDB collection '{collection_name}'.\n")

    # 4. Semantic Search Queries
    print("-" * 65)
    print(" 🔍 RUNNING SEMANTIC VECTOR SEARCH QUERIES")
    print("-" * 65)

    test_queries = [
        "How much money can I get for home office setup furniture?",
        "Can I copy-paste company code into public AI models?",
        "What is the policy for carryover vacation days?"
    ]

    for q in test_queries:
        print(f"\n❓ QUERY: '{q}'")
        results = collection.query(
            query_texts=[q],
            n_results=1
        )
        
        retrieved_text = results["documents"][0][0]
        retrieved_meta = results["metadatas"][0][0]
        distance = results["distances"][0][0]
        
        print(f"   ✅ RETRIEVED CHUNK: {retrieved_meta['section']}")
        print(f"   📊 Distance Score: {distance:.4f} (lower distance = closer match)")
        print("   📄 Passage Snippet:")
        print("   " + "\n   ".join(retrieved_text.split("\n")[:3]) + "...")
        print("-" * 65)

    print("\n💡 KEY LESSON FOR INTERVIEWS:")
    print("1. Documents are chopped into Chunks with metadata (section, page, source).")
    print("2. ChromaDB embeds every chunk and stores it in vector space.")
    print("3. When a user asks a question in plain English, ChromaDB retrieves the exact matching chunk in <10ms!")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
