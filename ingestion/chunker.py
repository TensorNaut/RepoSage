import ast
import re

# ── helpers ──────────────────────────────────────────────────────────────────

def _chunk_by_lines(text: str, file_path: str, chunk_size: int = 60, overlap: int = 10) -> list[dict]:
    """
    Generic fallback: split any text file into overlapping line windows.
    overlap means the last N lines of one chunk repeat as the first N lines
    of the next — this preserves context at boundaries.
    """
    lines = text.splitlines()
    chunks = []
    start = 0

    while start < len(lines):
        end = start + chunk_size
        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines).strip()

        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "type":   "code",
                    "source": "code_file",
                    "path":   file_path,
                    "lines":  f"{start + 1}-{min(end, len(lines))}"
                }
            })

        start += chunk_size - overlap  # slide forward, keeping overlap

    return chunks


def _chunk_python_ast(source: str, file_path: str) -> list[dict]:
    """
    For .py files: extract each function and class as its own chunk using AST.
    AST = Abstract Syntax Tree — Python parses the code into a tree structure,
    and we can walk it to find where each function/class starts and ends.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # If parsing fails, fall back to line chunking
        return _chunk_by_lines(source, file_path)

    lines = source.splitlines()
    chunks = []

    for node in ast.walk(tree):
        # We only care about function definitions and class definitions
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        start_line = node.lineno - 1        # ast is 1-indexed, lists are 0-indexed
        end_line   = node.end_lineno        # end_lineno is exclusive already

        chunk_text = "\n".join(lines[start_line:end_line]).strip()

        if not chunk_text:
            continue

        node_type = "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class"

        chunks.append({
            "text": chunk_text,
            "metadata": {
                "type":      "code",
                "source":    "code_file",
                "path":      file_path,
                "name":      node.name,
                "node_type": node_type,
                "lines":     f"{node.lineno}-{node.end_lineno}"
            }
        })

    # If AST found nothing (e.g. a file with only top-level statements), fall back
    if not chunks:
        return _chunk_by_lines(source, file_path)

    return chunks


# ── Language-specific regex patterns ─────────────────────────────────────────

# Maps file extension → regex that matches the START of a function/class block
LANG_PATTERNS = {
    ".js":   re.compile(r"^(async\s+function|function|\w+\s*=\s*(async\s+)?\(|class)\s+\w*", re.MULTILINE),
    ".ts":   re.compile(r"^(async\s+function|function|\w+\s*=\s*(async\s+)?\(|class|interface)\s+\w*", re.MULTILINE),
    ".jsx":  re.compile(r"^(async\s+function|function|const\s+\w+\s*=|class)\s+\w*", re.MULTILINE),
    ".tsx":  re.compile(r"^(async\s+function|function|const\s+\w+\s*=|class)\s+\w*", re.MULTILINE),
    ".java": re.compile(r"^\s*(public|private|protected|static|\s)+[\w\<\>\[\]]+\s+\w+\s*\(", re.MULTILINE),
    ".cpp":  re.compile(r"^\w[\w\s\*&]+\s+\w+\s*\([^)]*\)\s*\{", re.MULTILINE),
    ".c":    re.compile(r"^\w[\w\s\*&]+\s+\w+\s*\([^)]*\)\s*\{", re.MULTILINE),
    ".go":   re.compile(r"^func\s+\w+", re.MULTILINE),
    ".rs":   re.compile(r"^(pub\s+)?fn\s+\w+", re.MULTILINE),
}

def _chunk_by_regex(source: str, file_path: str, ext: str) -> list[dict]:
    """
    Find where each function/class starts using regex,
    then treat everything between two matches as one chunk.
    """
    pattern = LANG_PATTERNS[ext]
    matches = list(pattern.finditer(source))

    if not matches:
        return _chunk_by_lines(source, file_path)

    lines = source.splitlines()
    chunks = []

    for i, match in enumerate(matches):
        start_char = match.start()
        end_char   = matches[i + 1].start() if i + 1 < len(matches) else len(source)

        chunk_text = source[start_char:end_char].strip()
        start_line = source[:start_char].count("\n") + 1

        if chunk_text:
            chunks.append({
                "text": chunk_text[:3000],  # cap very long functions
                "metadata": {
                    "type":      "code",
                    "source":    "code_file",
                    "path":      file_path,
                    "name":      match.group(0).strip()[:60],
                    "node_type": "function_or_class",
                    "lines":     f"{start_line}-?"
                }
            })

    return chunks


def chunk_code_files(files: list[dict]) -> list[dict]:
    all_chunks = []

    for file in files:
        path    = file["path"]
        content = file["content"]

        if not content.strip():
            continue

        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""

        if ext == ".py":
            chunks = _chunk_python_ast(content, path)
        elif ext in LANG_PATTERNS:
            chunks = _chunk_by_regex(content, path, ext)
        else:
            chunks = _chunk_by_lines(content, path)

        all_chunks.extend(chunks)

    return all_chunks

# ── public API ────────────────────────────────────────────────────────────────

def chunk_code_files(files: list[dict]) -> list[dict]:
    """
    Takes the raw list from GitHubClient.get_code_files()
    Returns a flat list of chunks, each with text + metadata.
    """
    all_chunks = []

    for file in files:
        path    = file["path"]
        content = file["content"]

        if not content.strip():
            continue

        if path.endswith(".py"):
            chunks = _chunk_python_ast(content, path)
        else:
            chunks = _chunk_by_lines(content, path)

        all_chunks.extend(chunks)

    return all_chunks


def chunk_commits(commits: list[dict]) -> list[dict]:
    """
    Each commit becomes one chunk.
    We format it as a readable sentence so the embedding captures meaning,
    not just raw key-value pairs.
    """
    chunks = []

    for commit in commits:
        # Clean up message — remove [skip ci], extra newlines, etc.
        message = commit["message"].split("\n")[0].strip()  # first line only

        text = (
            f"Commit by {commit['author']} on {commit['date'][:10]}:\n"
            f"{message}\n"
            f"URL: {commit['url']}"
        )

        chunks.append({
            "text": text,
            "metadata": {
                "type":   "commit",
                "source": "commit_history",
                "sha":    commit["sha"],
                "author": commit["author"],
                "date":   commit["date"],
                "url":    commit["url"]
            }
        })

    return chunks


def chunk_issues(issues: list[dict]) -> list[dict]:
    """
    Each issue becomes one chunk: title + body combined.
    Labels are stored in metadata for filtering later.
    """
    chunks = []

    for issue in issues:
        # Truncate very long bodies to avoid hitting embedding limits
        body = issue["body"][:2000] if issue["body"] else "No description."

        text = (
            f"Issue #{issue['id']} [{issue['state'].upper()}]: {issue['title']}\n\n"
            f"{body}"
        )

        chunks.append({
            "text": text,
            "metadata": {
                "type":   "issue",
                "source": "issue_tracker",
                "id":     str(issue["id"]),
                "state":  issue["state"],
                "labels": ", ".join(issue["labels"]),
                "date":   issue["date"],
                "url":    issue["url"]
            }
        })

    return chunks