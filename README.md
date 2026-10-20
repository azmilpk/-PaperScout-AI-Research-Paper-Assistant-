# 📄 PaperScout — AI Research Paper Assistant

> Production-grade **Research Paper Assistant** powered by **LangChain (LCEL)**, **ChromaDB Vector Store**, **Real LLMs (Hugging Face / Gemini / OpenAI)**, and **Multi-PDF Document Management** with exact in-line citations and query routing.

---

## 🌟 Key Architecture & Highlights

- **Multi-Paper Library Management**: Ingest multiple conference / arXiv PDFs simultaneously with page-by-page metadata, section detection, and individual paper deletion.
- **Query Router & Anti-Hallucination Guardrails**: Semantic classification routing greetings and chitchat into natural conversations, while forcing technical questions through strict grounded RAG with the "I don't know" rule.
- **Accurate In-Line Citations**: Maps generated claims directly to numbered source tags: `[1] Attention Is All You Need (Page 3, Section 3.2)` with interactive passage inspection.
- **Multi-Model Support**: Native support for **free Hugging Face models** (`mistralai/Mistral-7B-Instruct-v0.3`, `Llama-3.2`), **Google Gemini**, and **OpenAI**.
- **ChromaDB Vector Store with Filtered Search**: Query across all papers or lock retrieval strictly to a selected active paper.
- **Zero-Cost Local Embeddings**: On-device vector embeddings running on ONNX MiniLM (no rate limits or API costs during PDF indexing).

---

## 🏗️ Architecture Flow

```
[ User Query: e.g. "What is Scaled Dot-Product Attention?" ]
       │
       ▼
 [ Query Router / Intent Classifier ]
       ├── If Greeting ("hai", "hello") ──► Friendly AI conversational reply
       │
       └── If Technical Question:
              │
              ▼
       [ ChromaDB Vector Search (Filtered by Paper ID) ]
              │
              ▼
       [ Top-k Retrieved Page Passages + Similarity Scores ]
              │
              ▼
       [ Strict Grounded Prompt: ChatPromptTemplate ]
              │
              ▼
       [ Real LLM: Hugging Face / Gemini / OpenAI (Temp = 0.1) ]
              │
              ▼
       [ Answer with Numbered Citations: [1] Paper Title (Page X, Section Y) ]
```

---

## 📂 Project Structure

```
documind-rag/
├── backend/
│   ├── main.py                     # FastAPI server: /papers, /upload, /chat, /settings
│   ├── rag_service.py              # PaperScout RAG Pipeline, ChromaDB store, Query Router
│   ├── requirements.txt            # Python dependencies (langchain, chromadb, etc.)
│   ├── data/
│   │   ├── papers_registry.json    # Tracked research papers & page stats
│   │   └── sample_papers/          # Bundled foundational papers (Attention Is All You Need)
│   └── .env.example                # LLM key template (Hugging Face, Gemini, OpenAI)
├── frontend/
│   ├── src/
│   │   ├── api/client.js           # API client with multi-paper & chat endpoints
│   │   ├── components/
│   │   │   ├── ApiKeyModal.jsx     # LLM key configuration modal
│   │   │   ├── ChatMessage.jsx     # Chat bubbles with model badge & in-text citation links
│   │   │   └── CitationCard.jsx    # Passage cards with page tags & relevance scores
│   │   ├── App.jsx                 # PaperScout dashboard (Sidebar, Paper Pill, Library, Q&A)
│   │   └── App.css                 # Dark mode UI matching modern research tools
│   └── package.json
└── README.md
```

---

## 🚀 Getting Started

### 1. Set Up Backend

Create `backend/.env` with your preferred free LLM token:

```env
# Option 1: Hugging Face Free Open-Source Models (https://huggingface.co/settings/tokens)
HUGGINGFACEHUB_API_TOKEN=your_hf_token_here
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.3

# Option 2: Google Gemini (https://aistudio.google.com/app/apikey)
# GOOGLE_API_KEY=your_gemini_key_here
# GEMINI_MODEL=gemini-2.5-flash

# Fast on-device vector embeddings (no quota used)
EMBEDDING_PROVIDER=local
```

Start the backend:

```powershell
cd d:\AI projects\documind-rag\backend
.\.venv\Scripts\uvicorn main:app --reload --port 8000

```

### 2. Start Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. 
* Click **"Load 'Attention Is All You Need'"** to start immediately with the bundled paper, or upload any research PDF from your computer!

---

## 🗺️ Project Roadmap
- [x] **Phase 1: Core Document Management & Multi-PDF Parsing** (Active paper pill, ChromaDB multi-paper indexing, query routing)
- [ ] **Phase 2: Deep Grounded Q&A with In-Text Formula & Architecture Diagrams**
- [ ] **Phase 3: Automated Paper Summarizer Engine** (Key Findings, Methodology, Limitations)
- [ ] **Phase 4: Cross-Paper Comparative Analysis** (`Compare` mode for 2+ papers)
- [ ] **Phase 5: Notes Scratchpad & Export**
