from ingestion.github_client import GitHubClient


client = GitHubClient(
    owner="tiangolo",
    repo="fastapi"
)

client.get_commits()