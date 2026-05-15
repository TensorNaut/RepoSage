import os
import requests
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.token = os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError("GitHub token not found in .env")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        })

    def get_commits(self, max_commits: int = 500) -> list[dict]:
        commits = []
        page = 1

        while len(commits) < max_commits:
            endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"
            response = self.session.get(endpoint, params={
                "per_page": 100,   # max allowed per page
                "page": page
            })

            if response.status_code != 200:
                raise Exception(f"GitHub API Error: {response.status_code} - {response.text}")

            batch = response.json()

            if not batch:           # empty page = no more commits
                break

            for raw in batch:
                commits.append({
                    "sha":     raw["sha"],
                    "message": raw["commit"]["message"],
                    "author":  raw["commit"]["author"]["name"],
                    "date":    raw["commit"]["author"]["date"],
                    "url":     raw["html_url"]
                })

                if len(commits) >= max_commits:
                    break

            page += 1

        return commits

    def get_issues(self, max_issues: int = 500) -> list[dict]:
        issues = []
        page = 1

        while len(issues) < max_issues:
            endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/issues"
            response = self.session.get(endpoint, params={
                "state": "all",    # open + closed
                "per_page": 100,
                "page": page
            })

            if response.status_code != 200:
                raise Exception(f"GitHub API Error: {response.status_code} - {response.text}")

            batch = response.json()

            if not batch:
                break

            for raw in batch:
                # GitHub issues API also returns pull requests — skip them
                if "pull_request" in raw:
                    continue

                issues.append({
                    "id":     raw["number"],
                    "title":  raw["title"],
                    "body":   raw["body"] or "",
                    "state":  raw["state"],
                    "labels": [l["name"] for l in raw["labels"]],
                    "date":   raw["created_at"],
                    "url":    raw["html_url"]
                })

                if len(issues) >= max_issues:
                    break

            page += 1

        return issues

    def get_code_files(self, extensions: list[str] = None) -> list[dict]:
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".md"]

        # Fetch the full file tree recursively in one API call
        endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/git/trees/HEAD"
        response = self.session.get(endpoint, params={"recursive": "1"})

        if response.status_code != 200:
            raise Exception(f"GitHub API Error: {response.status_code} - {response.text}")

        tree = response.json().get("tree", [])

        files = []
        for item in tree:
            # Only blobs (files), not trees (directories)
            if item["type"] != "blob":
                continue

            path = item["path"]
            if not any(path.endswith(ext) for ext in extensions):
                continue

            # Fetch raw file content
            raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/HEAD/{path}"
            file_response = self.session.get(raw_url)

            if file_response.status_code != 200:
                continue

            files.append({
                "path":    path,
                "content": file_response.text
            })

        return files
    
    def get_readme(self) -> str:
        """Fetch the README content directly."""
        for filename in ["README.md", "readme.md", "README.rst", "README.txt"]:
            raw_url = f"https://raw.githubusercontent.com/{self.owner}/{self.repo}/HEAD/{filename}"
            response = self.session.get(raw_url)
            if response.status_code == 200:
                return response.text
        return ""