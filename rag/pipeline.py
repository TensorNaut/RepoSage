import os
import re
from groq import Groq
from dotenv import load_dotenv
from ingestion.vector_store import query_collection, load_project_context, query_by_file
from ingestion.summarizer import format_summary_for_context
import streamlit as st

load_dotenv()

api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
client = Groq(api_key=api_key)


# ── Query Router ──────────────────────────────────────────────────────────────

def route_query(question: str) -> list[str]:
    q = question.lower()

    # Broad overview questions → search everything
    overview_keywords = [
    "about", "what is", "overview", "explain", "describe",
    "purpose", "goal", "how does it work", "how it works",
    "how does this work", "works"
]
    if any(word in q for word in overview_keywords):
        return ["code", "commits", "issues"]

    commit_keywords = ["when", "who", "last time", "changed", "fixed", "commit", "version", "update", "release"]
    issue_keywords  = ["bug", "issue", "problem", "error", "broken", "open", "closed", "report"]
    code_keywords   = ["how", "where", "what", "implement", "function", "class", "work", "does", "code", "architecture", "pipeline"]

    collections = []
    if any(word in q for word in commit_keywords): collections.append("commits")
    if any(word in q for word in issue_keywords):  collections.append("issues")
    if any(word in q for word in code_keywords):   collections.append("code")

    return collections or ["code", "commits", "issues"]


# ── Context Builder ───────────────────────────────────────────────────────────

def build_context(question: str, n_results: int = 6) -> str:
    context_parts = []
    total_used = 0

    # ── Always inject project summary ─────────────────────────────────────────
    project_summary = load_project_context()
    if project_summary:
        context_parts.append(format_summary_for_context(project_summary))

    # ── Check if question is about a specific file ────────────────────────────
    file_mention = extract_file_mention(question)

    if file_mention:
        # Direct metadata filter — get all chunks from that file
        results = query_by_file(file_mention)

        if results:
            context_parts.append(f"### FILE CONTENTS: {file_mention} ###")
            for r in results:
                meta = r["metadata"]
                label = f"[File: {meta.get('path', '?')} | {meta.get('node_type', 'code')} {meta.get('name', '')}]"
                context_parts.append(f"{label}\n{r['text']}\n")
                total_used += 1
        else:
            context_parts.append(
                f"### NOTE ###\nThe file '{file_mention}' was not found in the indexed repository.\n"
            )

        # Also do a semantic search so we get related context
        semantic = query_collection("code", question, n_results=3)
        related = [r for r in semantic if r["score"] >= 0.15 and
                   file_mention not in r["metadata"].get("path", "")]
        if related:
            context_parts.append("### RELATED CODE ###")
            for r in related:
                context_parts.append(
                    f"[File: {r['metadata'].get('path', '?')}]\n{r['text']}\n"
                )
            total_used += len(related)

    else:
        # Normal semantic search flow
        collections = route_query(question)
        q = question.lower()
        is_overview = any(w in q for w in [
            "about", "what is", "overview", "describe", "purpose",
            "how does it work", "how it works", "works"
        ])

        for collection in collections:
            results = query_collection(collection, question, n_results=n_results)
            if not results:
                continue

            if is_overview and collection == "code":
                readme_chunks = [r for r in results if "readme" in r["metadata"].get("path", "").lower()]
                other_chunks  = [r for r in results if "readme" not in r["metadata"].get("path", "").lower()]
                results = readme_chunks + other_chunks

            section_parts = []
            for r in results:
                if r["score"] < 0.15:
                    continue
                meta = r["metadata"]
                if meta.get("type") == "code":
                    label = f"[File: {meta.get('path', '?')}]"
                elif meta.get("type") == "commit":
                    label = f"[Commit by {meta.get('author', '?')} on {meta.get('date', '?')[:10]}]"
                elif meta.get("type") == "issue":
                    label = f"[Issue #{meta.get('id', '?')} - {meta.get('state', '?')}]"
                else:
                    label = "[Source]"

                section_parts.append(f"{label}\n{r['text']}\n")
                total_used += 1

            if section_parts:
                context_parts.append(f"### From {collection.upper()} ###")
                context_parts.extend(section_parts)

    if total_used == 0 and not project_summary:
        return "NO_RELEVANT_CONTEXT"

    return "\n".join(context_parts)


#── File Mention Detection ───────────────────────────────────────────────────

FILE_PATTERN = re.compile(
    r"\b[\w][\w/\\.-]*\.(py|js|ts|jsx|tsx|java|cpp|c|go|rs|md|txt|yaml|yml|json|html|css)\b",
    re.IGNORECASE
)

def extract_file_mention(question: str) -> str | None:
    """
    Detects if the user is asking about a specific file.
    Returns the filename string, or None.
    """
    match = FILE_PATTERN.search(question)
    if match:
        return match.group(0)  # full match e.g. "app.py", "llm/generator.py"
    return None

# ── General Knowledge Detection ─────────────────────────────────────────────

GENERAL_KNOWLEDGE_KEYWORDS = [
    "better than", "alternative to", "compared to", "vs ", "versus",
    "how does", "what is", "why use", "explain", "difference between",
    "pros and cons", "best practice", "industry standard"
]

def is_general_knowledge_question(question: str) -> bool:
    """
    Detect if the question is about general tech concepts
    rather than something specific to the indexed repo.
    """
    q = question.lower()
    return any(kw in q for kw in GENERAL_KNOWLEDGE_KEYWORDS)

# ── LLM Call ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are RepoSage, an AI assistant that helps developers explore and understand GitHub repositories.

You will receive context retrieved from the repository — source code, commit history, and issues.

Core rules:
- Base your answer entirely on the provided context. Do not use external knowledge to fill gaps.
- If the context is insufficient, say: "The indexed repository doesn't have enough information to answer this fully." Then share what you did find.
- Never invent function names, file paths, or behaviors not present in the context.

How to answer:
- Explain things clearly for someone new to the codebase — use plain English, not just code dumps.
- Synthesize across multiple retrieved snippets when they relate to the same topic.
- Always cite sources: mention file paths, function names, commit dates, or issue numbers.
- If asked for code, show the exact code from context with its file path.
- If context is partial, explain what you found and what's unclear.
- Keep answers concise but complete. Developers want clarity, not padding.
"""

def ask(question: str) -> str:
    print(f"\n🔍 Routing query: '{question}'")
    collections = route_query(question)
    print(f"   Searching: {collections}")

    context = build_context(question)
    general = is_general_knowledge_question(question)

    # If no repo context AND it's a general question → answer from training data
    if context == "NO_RELEVANT_CONTEXT" and general:
        messages = [
            {
                "role": "system",
                "content": """You are a helpful AI assistant with deep knowledge of software engineering, 
machine learning, and developer tools. Answer the question from your general knowledge.
Always start your response with: '⚠️ General Knowledge (not from the indexed repository):\n'
Be accurate and concise."""
            },
            {"role": "user", "content": question}
        ]
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content

    # No context, not a general question → hard stop
    if context == "NO_RELEVANT_CONTEXT":
        return "I don't have enough information in the indexed repository to answer this."

    # Normal RAG flow — repo context available
    # If it's also a general question, tell the LLM to prefer repo context but can supplement
    system = SYSTEM_PROMPT
    if general:
        system += "\nNote: This question may have a general knowledge dimension. Answer primarily from the context, but you may briefly supplement with well-known facts clearly labeled as 'General context:'."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=1024
    )

    return response.choices[0].message.content

