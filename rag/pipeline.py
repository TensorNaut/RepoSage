import os
from groq import Groq
from dotenv import load_dotenv
from ingestion.vector_store import query_collection

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Query Router ──────────────────────────────────────────────────────────────

def route_query(question: str) -> list[str]:
    """
    Decide which collections to search based on question keywords.
    Returns a list of collection names to query.
    """
    q = question.lower()

    commit_keywords = ["when", "who", "last time", "changed", "fixed", "commit", "version", "update", "release"]
    issue_keywords  = ["bug", "issue", "problem", "error", "broken", "open", "closed", "report"]
    code_keywords   = ["how", "where", "what", "implement", "function", "class", "work", "does", "code"]

    collections = []

    if any(word in q for word in commit_keywords):
        collections.append("commits")

    if any(word in q for word in issue_keywords):
        collections.append("issues")

    if any(word in q for word in code_keywords):
        collections.append("code")

    # Default: search all if nothing matched
    if not collections:
        collections = ["code", "commits", "issues"]

    return collections


# ── Context Builder ───────────────────────────────────────────────────────────

def build_context(question: str, n_results: int = 4) -> str:
    """
    Route the query, retrieve from relevant collections,
    and format everything into a context string for the LLM.
    """
    collections = route_query(question)
    context_parts = []

    for collection in collections:
        results = query_collection(collection, question, n_results=n_results)

        if not results:
            continue

        # Label each section so the LLM knows where the info came from
        context_parts.append(f"### From {collection.upper()} ###")

        for r in results:
            meta = r["metadata"]
            score = r["score"]

            # Only include reasonably relevant results
            if score < 0.2:
                continue

            # Add source label based on type
            if meta.get("type") == "code":
                label = f"[File: {meta.get('path', '?')}]"
            elif meta.get("type") == "commit":
                label = f"[Commit by {meta.get('author', '?')} on {meta.get('date', '?')[:10]}]"
            elif meta.get("type") == "issue":
                label = f"[Issue #{meta.get('id', '?')} - {meta.get('state', '?')}]"
            else:
                label = "[Source unknown]"

            context_parts.append(f"{label}\n{r['text']}\n")

    return "\n".join(context_parts) if context_parts else "No relevant context found."


# ── LLM Call ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are RepoSage, an expert AI assistant that answers questions about GitHub repositories.

You will be given context retrieved from the repository — which may include source code, commit history, and issues.

Rules:
- Answer ONLY based on the provided context
- If the context doesn't contain enough information, say so clearly
- For code questions, reference specific file paths and function names
- For commit questions, mention dates and authors
- For issue questions, mention the issue number and status
- Be concise and developer-focused
"""

def ask(question: str) -> str:
    """
    Full RAG pipeline: route → retrieve → build context → ask LLM → return answer.
    """
    print(f"\n🔍 Routing query: '{question}'")
    collections = route_query(question)
    print(f"   Searching: {collections}")

    context = build_context(question)

    if context == "No relevant context found.":
        return "I couldn't find relevant information in this repository to answer your question."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # free tier, very capable
        messages=messages,
        temperature=0.2,                    # low = more factual, less creative
        max_tokens=1024
    )

    return response.choices[0].message.content