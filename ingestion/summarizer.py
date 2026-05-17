import os
from groq import Groq
from dotenv import load_dotenv
import streamlit as st

load_dotenv()
api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
client = Groq(api_key=api_key)

SUMMARIZE_PROMPT = """You are analyzing a GitHub repository. Based on the README below, extract a structured project summary.

Return ONLY a JSON object with these exact keys:
{{
  "project_name": "name of the project",
  "description": "2-3 sentence description of what this project does",
  "tech_stack": ["list", "of", "main", "technologies"],
  "architecture": "brief description of the system architecture",
  "key_features": ["main feature 1", "main feature 2"],
  "entry_points": ["main files or commands to run the project"],
  "purpose": "who is this for and what problem does it solve"
}}

README content:
{readme}
"""

def generate_project_summary(readme: str, owner: str, repo: str) -> dict:
    """Use LLM to extract structured understanding of the project from README."""

    if not readme.strip():
        return {
            "project_name": repo,
            "description": "No README found in this repository.",
            "tech_stack": [],
            "architecture": "Unknown",
            "key_features": [],
            "entry_points": [],
            "purpose": "Unknown"
        }

    # Truncate very long READMEs — first 6000 chars is enough for summary
    readme_truncated = readme[:6000]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZE_PROMPT.format(readme=readme_truncated)
                }
            ],
            temperature=0.1,
            max_tokens=1024
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if LLM wrapped it
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        import json
        summary = json.loads(raw.strip())
        summary["repo"] = f"{owner}/{repo}"
        return summary

    except Exception as e:
        print(f"⚠️  Summary generation failed: {e}")
        return {
            "project_name": repo,
            "repo": f"{owner}/{repo}",
            "description": "Could not generate summary.",
            "tech_stack": [],
            "architecture": "Unknown",
            "key_features": [],
            "entry_points": [],
            "purpose": "Unknown"
        }


def format_summary_for_context(summary: dict) -> str:
    """Convert the summary dict into a readable string for LLM context injection."""
    if not summary:
        return ""

    tech = ", ".join(summary.get("tech_stack", [])) or "Not specified"
    features = "\n".join(f"  - {f}" for f in summary.get("key_features", []))
    entry = ", ".join(summary.get("entry_points", [])) or "Not specified"

    return f"""### PROJECT OVERVIEW (Always relevant) ###
Project: {summary.get("project_name", "Unknown")} ({summary.get("repo", "")})
Description: {summary.get("description", "")}
Purpose: {summary.get("purpose", "")}
Tech Stack: {tech}
Architecture: {summary.get("architecture", "")}
Key Features:
{features}
Entry Points: {entry}
"""