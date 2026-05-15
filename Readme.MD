# RepoSage

> **Ask anything about any GitHub repository — code, commits, or issues — in plain English.**

RepoSage is an AI-powered developer assistant that lets you point it at any public GitHub repository and have a natural conversation about it. It understands the codebase, commit history, and issue tracker simultaneously.

---

## What Can You Ask?

- *"How does authentication work in this codebase?"*
- *"When was the last memory leak fixed and who fixed it?"*
- *"Are there any open issues related to rate limiting?"*
- *"What files does the payment module depend on?"*
- *"Walk me through the data pipeline of this project."*
- *"Are there any potential bugs in the ingestion logic?"*

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
- **Smart query routing** — automatically decides which data sources to search based on question intent
- **Project-level context injection** — README is summarized by LLM at ingest time and prepended to every query, so the model always understands what the project is
- **Hallucination prevention** — strict score filtering and hard stops before LLM call when no relevant context exists
- **General knowledge hybrid** — detects general tech questions and answers from training data with a clear label
- **Persistent vector store** — ChromaDB stores embeddings locally; no re-indexing needed between sessions
- **Interactive Streamlit UI** — sidebar shows live project summary, tech stack, and key features

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
├── app.py                    # Streamlit web UI
├── ingest.py                 # CLI ingestion script (run once per repo)
├── ask.py                    # CLI query loop
│
├── ingestion/
│   ├── __init__.py
│   ├── github_client.py      # GitHub API — fetches commits, issues, code, README
│   ├── chunker.py            # AST + regex + line-based chunking
│   ├── vector_store.py       # ChromaDB read/write operations
│   └── summarizer.py         # LLM-powered README → project summary
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
git clone https://github.com/your-username/RepoSage.git
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
- **GitHub PAT:** GitHub → Settings → Developer Settings → Personal Access Tokens → Generate (select `repo` scope)
- **Groq API Key:** [console.groq.com](https://console.groq.com) → API Keys → Create

### 3. Run the Streamlit UI

```bash
streamlit run app.py
```

Enter any public GitHub repo URL in the sidebar, click **Index Repository**, and start chatting.

---

## CLI Usage

If you prefer the terminal:

```bash
# Step 1 — ingest a repo (run once)
python ingest.py
# Enter GitHub repo URL: https://github.com/tiangolo/fastapi

# Step 2 — query it
python ask.py
# You: How does authentication work?
# You: When was the last dependency update?
# You: exit
```

---

## How It Works

### Ingestion Pipeline

1. **README → Project Summary** — The README is fetched and sent to Groq LLM, which extracts a structured summary (name, description, tech stack, architecture, key features). This is saved to `project_context.json`.

2. **Code Files** — All source files are fetched via the GitHub Trees API in one call. Python files are chunked at the function/class level using Python's `ast` module. JS/TS/Go/Rust/Java files use regex pattern matching. Everything else uses sliding window line chunking with overlap.

3. **Commits** — Each commit is formatted as a readable sentence with author, date, and message. Paginated up to your chosen limit.

4. **Issues** — Title + body combined into a single chunk with state and label metadata. Pull requests are filtered out.

5. **Embedding + Storage** — All chunks are embedded using `all-MiniLM-L6-v2` and stored in ChromaDB across three separate collections: `code`, `commits`, `issues`.

### Query Pipeline

1. **Query Router** — Keywords in the question determine which collections to search. Broad questions search all three.

2. **Context Assembly** — Project summary is always prepended. Retrieved chunks are filtered by relevance score (≥ 0.15) and labeled with their source.

3. **LLM Call** — Groq (Llama 3.3 70B) receives the assembled context and answers strictly from it. If no relevant context passes the threshold, the LLM is never called.


---

## Limitations

- Only **public** GitHub repositories are supported
- GitHub API rate limit: 5,000 requests/hour with a PAT
- Code indexing is limited to: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.go`, `.java`, `.cpp`, `.c`, `.md`
- Groq free tier has rate limits on requests per minute
- ChromaDB stores data locally — indexing a new repo overwrites the previous one

---

## 🗺️ Roadmap

- [ ] Support for private repositories
- [ ] Multi-repo indexing (compare two repos)
- [ ] Deployment on Streamlit Community Cloud
- [ ] CodeBERT / StarCoder embeddings for better code understanding
- [ ] Conversation memory across sessions
- [ ] Export Q&A sessions as markdown

---

## Acknowledgements

Built with:
- [ChromaDB](https://www.trychroma.com/) — vector database
- [sentence-transformers](https://www.sbert.net/) — local embeddings
- [Groq](https://groq.com/) — ultra-fast LLM inference
- [Streamlit](https://streamlit.io/) — web UI

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.