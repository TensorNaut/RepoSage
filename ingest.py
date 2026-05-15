from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues
from ingestion.vector_store import store_chunks, save_project_context
from ingestion.summarizer import generate_project_summary

github_url = input("Enter GitHub repo URL: ")
owner, repo = github_url.strip().rstrip("/").split("/")[-2:]
print(f"\nProcessing: {owner}/{repo}\n")

client = GitHubClient(owner=owner, repo=repo)

print("Fetching README and generating project summary...")
readme = client.get_readme()
summary = generate_project_summary(readme, owner, repo)
save_project_context(summary)
print(f"Project summary saved: {summary['description'][:80]}...\n")

print("Fetching data...")
commits = client.get_commits(max_commits=200)
issues  = client.get_issues(max_issues=100)
files   = client.get_code_files()

print("Chunking...")
commit_chunks = chunk_commits(commits)
issue_chunks  = chunk_issues(issues)
code_chunks   = chunk_code_files(files)
print(f"   {len(commit_chunks)} commit | {len(issue_chunks)} issue | {len(code_chunks)} code chunks\n")

print("Embedding + Storing...")
store_chunks(commit_chunks, "commits")
store_chunks(issue_chunks,  "issues")
store_chunks(code_chunks,   "code")

print("\nDone! Run ask.py or streamlit run app.py to start querying.")