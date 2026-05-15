import streamlit as st
from rag.pipeline import ask
from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues
from ingestion.vector_store import store_chunks, load_project_context, save_project_context, load_project_context
from ingestion.summarizer import format_summary_for_context, generate_project_summary

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RepoSage",
    page_icon="🔮",
    layout="wide"
)

st.title("🔮 RepoSage")
st.caption("Ask anything about any GitHub repository")

# ── Sidebar: repo ingestion ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## RepoSage")
    st.caption("Repository Intelligence Engine")

    st.divider()

    # =========================
    # REPO INPUT
    # =========================
    st.markdown("### 📦 Repository")

    repo_url = st.text_input(
        "GitHub Repository",
        placeholder="https://github.com/owner/repo",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns(2)

    with col1:
        max_commits = st.number_input(
            "Commits",
            min_value=50,
            max_value=2000,
            value=200,
            step=50
        )

    with col2:
        max_issues = st.number_input(
            "Issues",
            min_value=50,
            max_value=1000,
            value=100,
            step=50
        )

    st.caption(
        f"Indexing up to {max_commits} commits "
        f"and {max_issues} issues"
    )

    # =========================
    # INDEX BUTTON
    # =========================
    if st.button("🚀 Index Repository", use_container_width=True):
        if not repo_url.strip():
            st.error("Enter a valid GitHub repository URL.")
            st.stop()

        try:
            owner, repo = repo_url.strip().rstrip("/").split("/")[-2:]

            progress = st.progress(0)
            status   = st.empty()

            status.info("Fetching README and generating project summary...")
            client  = GitHubClient(owner=owner, repo=repo)
            readme  = client.get_readme()
            summary = generate_project_summary(readme, owner, repo)
            save_project_context(summary)

            progress.progress(15)
            status.info("Cloning repository metadata...")

            commits = client.get_commits(max_commits=int(max_commits))
            issues  = client.get_issues(max_issues=int(max_issues))
            files   = client.get_code_files()

            progress.progress(45)
            status.info("Chunking repository context...")

            commit_chunks = chunk_commits(commits)
            issue_chunks  = chunk_issues(issues)
            code_chunks   = chunk_code_files(files)

            progress.progress(65)
            status.info("Generating embeddings...")

            store_chunks(commit_chunks, "commits")
            store_chunks(issue_chunks,  "issues")
            store_chunks(code_chunks,   "code")

            progress.progress(100)
            st.session_state["repo_name"] = f"{owner}/{repo}"
            status.success("Repository indexed successfully.")

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Commits", len(commit_chunks))
            c2.metric("Issues",  len(issue_chunks))
            c3.metric("Code",    len(code_chunks))

        except Exception as e:
            st.error(f"Indexing failed: {str(e)}")

    # =========================
    # CURRENT REPO
    # =========================
    if "repo_name" in st.session_state:
        st.divider()
        st.markdown("### 🧠 Active Repository")
        st.code(st.session_state["repo_name"], language="bash")

    # Project summary display
    project_ctx = load_project_context()
    if project_ctx:
        st.divider()
        st.markdown("### 📋 Repository Context")
        st.markdown(f"#### {project_ctx.get('project_name', 'Unknown')}")

        if project_ctx.get("description"):
            st.caption(project_ctx["description"])

        if project_ctx.get("tech_stack"):
            st.markdown("##### Tech Stack")
            st.markdown(" ".join(f"`{t}`" for t in project_ctx["tech_stack"]))

        if project_ctx.get("key_features"):
            with st.expander("Key Features", expanded=False):
                for feature in project_ctx["key_features"]:
                    st.markdown(f"- {feature}")

        if project_ctx.get("architecture"):
            with st.expander("Architecture", expanded=False):
                st.markdown(project_ctx["architecture"])

    # =========================
    # FOOTER
    # =========================
    st.divider()

    st.caption(
        "Built with ChromaDB · SentenceTransformers · Groq"
    )

# ── Chat interface ────────────────────────────────────────────────────────────

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle new input
if prompt := st.chat_input("Ask something about the codebase..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get and show assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = ask(prompt)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})