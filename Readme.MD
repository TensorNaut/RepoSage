# RepoSage

> **Ask anything about any GitHub repository — code, commits, or issues — in plain English.**

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-f55036?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-6d28d9?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-00c853?style=flat-square)

RepoSage is an AI-powered developer assistant that lets you point it at any public GitHub repository and have a natural conversation about it. It understands the codebase, commit history, and issue tracker simultaneously — with no hallucination and full source citations.

---

## What Can You Ask?

```
"How does authentication work in this codebase?"
"When was the last memory leak fixed and who fixed it?"
"Are there any open issues related to rate limiting?"
"What files does the payment module depend on?"
"Walk me through the data pipeline of this project."
"Examine app.py and find potential bugs."
"Tell me about the architecture of this project."
```

---

## Architecture

```
                      GitHub Repo URL
                             ↓
                    Repo Ingestion Layer
  ┌─────────────────┬─────────────────┬─────────────────┐
  ↓                 ↓                 ↓                 ↓
README          Code Files          Commits          Issues
  ↓                 ↓                 ↓                 ↓
LLM Summary     AST/Regex          Structure        Structure
  ↓             Chunking          + Metadata       + Metadata
  ↓                 ↓                 ↓                 ↓
project_        Embeddings        Embeddings       Embeddings
context.json      └──────────────────┬──────────────────┘
                                     ↓
                                ChromaDB
                           (3 separate collections)
                                     ↓
                               Query Router
                            (routes by intent)
                                     ↓
                                Retriever
                           (top-k similarity search)
                                     ↓
                             Context Builder
                       (project summary + chunks)
                                     ↓
                              Groq LLM (Llama 3)
                                     ↓
                                  Response
```

---

## Key Features

- **Multi-source RAG** — searches code, commits, and issues simultaneously
- **AST-based code chunking** — Python functions/classes extracted precisely using Abstract Syntax Trees; regex fallback for JS, TS, Go, Rust, Java, C/C++
- **File-aware retrieval** — ask about a specific file (e.g. "examine app.py") and all its chunks are fetched via metadata filter, bypassing semantic search
- **Smart query routing** — automatically decides which data sources to search based on question intent
- **Project-level context injection** — README is summarized by LLM at ingest time and prepended to every query, so the model always understands what the project is
- **Hallucination prevention** — strict score filtering (≥ 0.15) and hard stop before LLM call when no relevant context exists
- **General knowledge hybrid** — detects general tech questions and answers from training data with a clear `⚠️ General Knowledge` label
- **Persistent vector store** — ChromaDB stores embeddings locally; no re-indexing needed between sessions
- **Retro TUI** — developer-focused terminal-style UI with live system status, file tree, and query context panel

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data Source | GitHub REST API |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) — local, free |
| Vector Database | ChromaDB (persistent, local) |
| LLM | Groq API — `llama-3.3-70b-versatile` (free tier) |
| UI | Streamlit |
| Language | Python 3.10+ |

---

## Project Structure

```
RepoSage/
├── app.py                    # Streamlit web UI (retro TUI style)
├── ingest.py                 # CLI ingestion script (run once per repo)
├── ask.py                    # CLI query loop
│
├── ingestion/
│   ├── __init__.py
│   ├── github_client.py      # GitHub API — fetches commits, issues, code, README
│   ├── chunker.py            # AST + regex + line-based chunking
│   ├── vector_store.py       # ChromaDB read/write + file-aware metadata query
│   └── summarizer.py         # LLM-powered README → structured project summary
│
├── rag/
│   ├── __init__.py
│   └── pipeline.py           # Query router + context builder + LLM call
│
├── chroma_db/                # Auto-created by ChromaDB (gitignored)
├── project_context.json      # Auto-created at ingest time (gitignored)
├── .env                      # API keys (gitignored)
└── requirements.txt
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/TensorNaut/RepoSage.git
cd RepoSage
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up API keys

Create a `.env` file in the project root:

```env
GITHUB_TOKEN=your_github_personal_access_token
GROQ_API_KEY=your_groq_api_key
```

**Getting your keys:**
- **GitHub PAT:** GitHub → Settings → Developer Settings → Personal Access Tokens → Generate (`repo` scope)
- **Groq API Key:** [console.groq.com](https://console.groq.com) → API Keys → Create

### 3. Run the Streamlit UI

```bash
streamlit run app.py
```

Enter any public GitHub repo URL, click **INDEX REPO**, and start chatting.

---

## CLI Usage

```bash
# Step 1 — ingest a repo (run once per repo)
python ingest.py
# Enter GitHub repo URL: https://github.com/tiangolo/fastapi

# Step 2 — query it interactively
python ask.py
# You: How does authentication work?
# You: When was the last dependency update?
# You: exit
```

---

## How It Works

### Ingestion Pipeline

1. **README → Project Summary** — README is fetched and sent to Groq LLM, which extracts a structured JSON summary (name, description, tech stack, architecture, key features). Saved to `project_context.json`.

2. **Code Files** — All source files fetched via GitHub Trees API in a single call. Python files chunked at function/class level using Python's `ast` module. JS/TS/Go/Rust/Java use regex pattern matching. Everything else uses sliding window line chunking with overlap.

3. **Commits** — Each commit formatted as a readable sentence with author, date, and message. Paginated up to your chosen limit.

4. **Issues** — Title + body combined into one chunk with state and label metadata. Pull requests are filtered out automatically.

5. **Embedding + Storage** — All chunks embedded using `all-MiniLM-L6-v2` and stored in ChromaDB across three separate named collections: `code`, `commits`, `issues`.

### Query Pipeline

1. **Query Router** — Keywords in the question determine which collections to search. Broad overview questions search all three.

2. **File Detection** — If the question mentions a filename (e.g. `app.py`, `llm/generator.py`), all chunks from that file are fetched via ChromaDB metadata filter rather than semantic search.

3. **Context Assembly** — Project summary always prepended. Retrieved chunks filtered by relevance score (≥ 0.15) and labeled with source file, commit author/date, or issue number.

4. **LLM Call** — Groq (Llama 3.3 70B) receives assembled context and answers strictly from it. If no relevant context passes the threshold, the LLM is never called — returning a direct "not enough information" message instead.

---

## Limitations

- Only **public** GitHub repositories are supported
- GitHub API rate limit: 5,000 requests/hour with a PAT
- Code indexing covers: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.go`, `.java`, `.cpp`, `.c`, `.md`
- Groq free tier has rate limits on requests per minute
- ChromaDB stores locally — indexing a new repo clears the previous one
- AST chunking works best on well-structured code; heavily procedural scripts may produce fewer chunks

---

## Future Work

- [ ] Support for private repositories (OAuth flow)
- [ ] Multi-repo indexing and cross-repo comparison
- [ ] Deployment on Streamlit Community Cloud
- [ ] CodeBERT / StarCoder embeddings for better code semantic understanding
- [ ] Conversation memory across sessions
- [ ] Export Q&A sessions as markdown reports

---

## Contributing

Pull requests are welcome. For major changes please open an issue first to discuss what you would like to change.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Open a pull request

---

## Acknowledgements

Built with:
- [ChromaDB](https://www.trychroma.com/) — vector database
- [sentence-transformers](https://www.sbert.net/) — local embeddings
- [Groq](https://groq.com/) — ultra-fast LLM inference
- [Streamlit](https://streamlit.io/) — web UI framework
- [GitHub REST API](https://docs.github.com/en/rest) — data source

---

## License

MIT License — see [LICENSE](LICENSE) for details.