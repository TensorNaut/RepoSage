from ingestion.github_client import GitHubClient

client = GitHubClient(owner="TensorNaut", repo="ExpenX")

# --- Commits ---
commits = client.get_commits(max_commits=200)
print(f"\n✅ Commits fetched: {len(commits)}")
for c in commits[:3]:
    print(c)

# --- Issues ---
issues = client.get_issues(max_issues=100)
print(f"\n✅ Issues fetched: {len(issues)}")
for i in issues[:3]:
    print(i)

# --- Code Files ---
files = client.get_code_files()
print(f"\n✅ Code files fetched: {len(files)}")
for f in files[:3]:
    print(f["path"], "→", len(f["content"]), "chars")