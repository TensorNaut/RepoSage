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

    def get_code_files(self):
        """
        Will return:
        [
            {
                "path": "...",
                "content": "..."
            }
        ]
        """
        pass

    def get_commits(self):
        endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"

        response = self.session.get(endpoint)

        if response.status_code != 200:
            raise Exception(
                f"GitHub API Error: {response.status_code} - {response.text}"
            )

        commits = response.json()

        print(commits)

        return commits

    def get_issues(self):
        """
        Will return:
        [
            {
                "title": "...",
                "body": "...",
                "labels": [...]
            }
        ]
        """
        pass