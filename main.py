from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues
from ingestion.vector_store import store_chunks, query_collection

client = GitHubClient(owner="tiangolo", repo="fastapi")

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

# ── Quick test query ──────────────────────────────────────────────────────────
print("\n🔍 Test Query: 'how does authentication work?'")
results = query_collection("code", "how does authentication work?", n_results=3)
for r in results:
    print(f"\n[Score: {r['score']}] {r['metadata']['path']}")
    print(r["text"][:200])