from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues

client = GitHubClient(owner="TensorNaut", repo="ExpenX")

commits = client.get_commits(max_commits=200)
issues  = client.get_issues(max_issues=100)
files   = client.get_code_files()

commit_chunks = chunk_commits(commits)
issue_chunks  = chunk_issues(issues)
code_chunks   = chunk_code_files(files)

print(f"Commit chunks : {len(commit_chunks)}")
print(f"Issue chunks  : {len(issue_chunks)}")
print(f"Code chunks   : {len(code_chunks)}")

if commit_chunks:
    print("\n--- Sample Commit Chunk ---")
    print(commit_chunks[1]["text"])
    print("Metadata:", commit_chunks[1]["metadata"])

if issue_chunks:
    print("\n--- Sample Issue Chunk ---")
    print(issue_chunks[0]["text"][:300])
    print("Metadata:", issue_chunks[0]["metadata"])

if code_chunks:
    print("\n--- Sample Code Chunk ---")
    print(code_chunks[0]["text"][:300])
    print("Metadata:", code_chunks[0]["metadata"])