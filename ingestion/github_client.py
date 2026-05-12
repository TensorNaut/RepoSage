import os
import json
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
            raise ValueError("GitHub token not found")

        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json"
        })

    def save_json(self, data, filename):

        os.makedirs("data", exist_ok=True)

        with open(f"data/{filename}", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_commits(self, max_commits=500):

        all_commits = []

        page = 1
        per_page = 100

        while len(all_commits) < max_commits:

            endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/commits"

            response = self.session.get(
                endpoint,
                params={
                    "per_page": per_page,
                    "page": page
                }
            )

            if response.status_code != 200:
                raise Exception(response.text)

            commits = response.json()

            if not commits:
                break

            for commit in commits:

                cleaned_commit = {
                    "sha": commit.get("sha"),
                    "message": commit.get("commit", {}).get("message"),
                    "author": commit.get("commit", {}).get("author", {}).get("name"),
                    "date": commit.get("commit", {}).get("author", {}).get("date"),
                    "url": commit.get("html_url")
                }

                all_commits.append(cleaned_commit)

                if len(all_commits) >= max_commits:
                    break

            page += 1

        self.save_json(all_commits, "commits.json")

        return all_commits

    def get_issues(self, max_issues=200):

        all_issues = []

        page = 1
        per_page = 100

        while len(all_issues) < max_issues:

            endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/issues"

            response = self.session.get(
                endpoint,
                params={
                    "state": "all",
                    "per_page": per_page,
                    "page": page
                }
            )

            if response.status_code != 200:
                raise Exception(response.text)

            issues = response.json()

            if not issues:
                break

            for issue in issues:

                # Skip pull requests
                if "pull_request" in issue:
                    continue

                cleaned_issue = {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "body": issue.get("body"),
                    "state": issue.get("state"),
                    "labels": [
                        label.get("name")
                        for label in issue.get("labels", [])
                    ],
                    "created_at": issue.get("created_at"),
                    "url": issue.get("html_url")
                }

                all_issues.append(cleaned_issue)

                if len(all_issues) >= max_issues:
                    break

            page += 1

        self.save_json(all_issues, "issues.json")

        return all_issues

    def get_code_files(self, extensions=[".py", ".md"]):

        collected_files = []

        def traverse(path=""):

            endpoint = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/contents/{path}"

            response = self.session.get(endpoint)

            if response.status_code != 200:
                return

            items = response.json()

            if not isinstance(items, list):
                return

            for item in items:

                if item["type"] == "dir":
                    traverse(item["path"])

                elif item["type"] == "file":

                    file_path = item.get("path", "")
                    file_size = item.get("size", 0)

                    if not any(file_path.endswith(ext) for ext in extensions):
                        continue

                    if file_size > 50000:
                        continue

                    download_url = item.get("download_url")

                    if not download_url:
                        continue

                    file_response = requests.get(download_url)

                    if file_response.status_code != 200:
                        continue

                    collected_files.append({
                        "path": file_path,
                        "content": file_response.text,
                        "size": file_size,
                        "url": item.get("html_url")
                    })

        traverse()

        self.save_json(collected_files, "code_files.json")

        return collected_files