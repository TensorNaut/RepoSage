from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues
from ingestion.vector_store import store_chunks
from rag.pipeline import ask

github_url = input("Enter GitHub repo URL (e.g., https://github.com/user/repo): ")
print(f"Processing repo: {github_url}\n")
# Extract owner and repo name from the URL
owner, repo = github_url.split("/")[-2:]
print(f"Owner: {owner}, Repo: {repo}\n")

client = GitHubClient(owner=owner, repo=repo)

print("Fetching data........")
commits = client.get_commits(max_commits=200)
issues  = client.get_issues(max_issues=100)
files   = client.get_code_files()

print("Chunking.........")
commit_chunks = chunk_commits(commits)
issue_chunks  = chunk_issues(issues)
code_chunks   = chunk_code_files(files)

print(f"   {len(commit_chunks)} commit chunks")
print(f"   {len(issue_chunks)} issue chunks")
print(f"   {len(code_chunks)} code chunks\n")

print("Embedding + Storing.........")
store_chunks(commit_chunks, "commits")
store_chunks(issue_chunks,  "issues")
store_chunks(code_chunks,   "code")

# ── Test the full RAG pipeline ────────────────────────────────────────────────
while True:
    q = input("\nAsk a question about the codebase (or 'exit' to quit): ")
    if q.lower() == "exit":
        break
    print("\n" + "="*60)
    print(f"Q: {q}")
    print("-"*60)
    print(ask(q))

# questions = [
#     "How does authentication work in this codebase?",
#     "When was the last dependency update and what was it?",
#     "Are there any open issues related to routing or custom routes?"
# ]

# for q in questions:
#     print("\n" + "="*60)
#     print(f"Q: {q}")
#     print("-"*60)
#     print(ask(q))