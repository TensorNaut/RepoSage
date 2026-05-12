def chunk_commits(commits):

    chunks = []

    for commit in commits:

        chunks.append({
            "id": f"commit_{commit['sha'][:8]}",
            "text": commit["message"],
            "metadata": {
                "type": "commit",
                "sha": commit["sha"],
                "author": commit["author"],
                "date": commit["date"],
                "url": commit["url"]
            }
        })

    return chunks


def chunk_issues(issues):

    chunks = []

    for issue in issues:

        text = f"{issue['title']}\n\n{issue['body'] or ''}"

        chunks.append({
            "id": f"issue_{issue['number']}",
            "text": text,
            "metadata": {
                "type": "issue",
                "number": issue["number"],
                "state": issue["state"],
                "labels": issue["labels"],
                "url": issue["url"]
            }
        })

    return chunks


def chunk_code_files(files):

    chunks = []

    chunk_size = 60
    overlap = 10

    for file in files:

        lines = file["content"].splitlines()

        start = 0
        chunk_index = 0

        while start < len(lines):

            end = start + chunk_size

            chunk_lines = lines[start:end]

            chunk_text = "\n".join(chunk_lines)

            chunks.append({
                "id": f"code_{file['path'].replace('/', '_')}_{chunk_index}",
                "text": chunk_text,
                "metadata": {
                    "type": "code",
                    "path": file["path"],
                    "chunk_index": chunk_index,
                    "url": file["url"]
                }
            })

            start += (chunk_size - overlap)

            chunk_index += 1

    return chunks