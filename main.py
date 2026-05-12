import json

from ingestion.github_client import GitHubClient

from ingestion.chunker import (
    chunk_commits,
    chunk_issues,
    chunk_code_files
)


client = GitHubClient(
    owner="TensorNaut",
    repo="NLP-hatchling"
)

client.get_commits()
client.get_issues()
client.get_code_files()


commits = json.load(open("data/commits.json", encoding="utf-8"))
issues = json.load(open("data/issues.json", encoding="utf-8"))
files = json.load(open("data/code_files.json", encoding="utf-8"))


commit_chunks = chunk_commits(commits)

issue_chunks = chunk_issues(issues)

code_chunks = chunk_code_files(files)


print(f"Commit chunks: {len(commit_chunks)}")

print(f"Issue chunks: {len(issue_chunks)}")

print(f"Code chunks: {len(code_chunks)}")

print("\nSample commit chunk:\n")

print(commit_chunks[0])

print("\nSample code chunk:\n")

print(code_chunks[0])