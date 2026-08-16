"""
====================================================================
STEP 1: Demystifying Vectors, Embeddings & Cosine Similarity
====================================================================

WHAT IS AN EMBEDDING?
An embedding model turns any text into a list of numbers (Vector).
Each dimension in the vector represents a hidden "feature" or "meaning concept".

In this visual mini-demo:
Vector = [Tech/Code, Animals/Pets, Vehicles/Auto, Playfulness]
====================================================================
"""

import sys
import numpy as np

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# 1. Define sample sentences
sentences = [
    "The dog chased the ball",            # Sentence A
    "A puppy ran after the toy",           # Sentence B (Same meaning, different words)
    "Python code for FastAPI backend",     # Sentence C (Coding / Tech)
    "Car engine oil change manual",       # Sentence D (Automotive)
]

# 2. Simulated Vector Embeddings (in real AI, models like Gemini or OpenAI generate 768 or 1536 numbers)
# Dimensions: [Tech, Animals, Vehicles, Playfulness]
vectors = {
    "The dog chased the ball":        np.array([0.05, 0.90, 0.05, 0.85]),
    "A puppy ran after the toy":       np.array([0.02, 0.92, 0.05, 0.88]),
    "Python code for FastAPI backend": np.array([0.95, 0.01, 0.05, 0.10]),
    "Car engine oil change manual":   np.array([0.10, 0.05, 0.92, 0.15]),
}

def cosine_similarity(vec_a, vec_b):
    """
    Calculates Cosine Similarity between two vectors.
    Formula: (A · B) / (||A|| * ||B||)
    Result: 
      1.0  = Perfect match in meaning
      0.0  = Completely unrelated
     -1.0  = Exact opposite
    """
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    return dot_product / (norm_a * norm_b)


def run_demo():
    print("=" * 65)
    print(" 🚀 AI CONCEPT DEMO: VECTORS & COSINE SIMILARITY")
    print("=" * 65)
    
    query = "The dog chased the ball"
    query_vec = vectors[query]
    
    print(f"\n📌 QUERY SENTENCE: '{query}'")
    print(f"   Vector Representation: {query_vec}\n")
    print("-" * 65)
    print(f"{'Target Sentence':<36} | {'Similarity Score':<16} | {'Match Type'}")
    print("-" * 65)
    
    for text, vec in vectors.items():
        score = cosine_similarity(query_vec, vec)
        
        if score > 0.95:
            match_type = "🎯 Identical / High Similarity"
        elif score > 0.70:
            match_type = "✅ Related Context"
        else:
            match_type = "❌ Unrelated Concept"
            
        print(f"{text:<36} | {score*100:6.2f}%          | {match_type}")
        
    print("-" * 65)
    print("\n💡 KEY LESSON FOR RAG & INTERVIEWS:")
    print("1. 'The dog chased the ball' and 'A puppy ran after the toy' have NO shared words except 'the'.")
    print("2. Yet, their Vector Similarity score is ~99.8%!")
    print("3. This is why Vector Databases enable AI to find exact answers based on MEANING, not just keywords.")
    print("=" * 65)

if __name__ == "__main__":
    run_demo()
