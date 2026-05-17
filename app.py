import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from datetime import datetime

from rag.pipeline import ask, extract_file_mention, route_query
from ingestion.github_client import GitHubClient
from ingestion.chunker import chunk_code_files, chunk_commits, chunk_issues
from ingestion.vector_store import (
    store_chunks, save_project_context,
    load_project_context, list_indexed_files
)
from ingestion.summarizer import generate_project_summary

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RepoSage",
    page_icon="reposage.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

html, body, [class*="css"] {
    font-family: 'Share Tech Mono', 'Courier New', monospace !important;
    background-color: #080808 !important;
    color: #e8e8e8 !important;
    overflow: hidden !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0.4rem 0.8rem !important;
    max-width: 100% !important;
    height: 100vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
}
.block-container::-webkit-scrollbar {
    display: none !important;
}
[data-testid="stSidebar"] { display: none; }
div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

/* Inputs and buttons */
input, textarea, select {
    background-color: #0a0800 !important;
    color: #ffb000 !important;
    border: 1px solid #7a5500 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 14px !important;
}
input:focus { border-color: #ffb000 !important; box-shadow: none !important; }

.stButton > button {
    background: #0a0800 !important;
    color: #ffb000 !important;
    border: 1px solid #ffb000 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 13px !important;
    letter-spacing: 1px !important;
    width: 100% !important;
    padding: 8px !important;
}
.stButton > button:hover {
    background: #ffb000 !important;
    color: #080808 !important;
}

/* Number input */
[data-testid="stNumberInput"] input { text-align: center !important; }
[data-testid="stNumberInput"] button {
    background: #0a0800 !important;
    border: 1px solid #1a1a1a !important;
    color: #7a5500 !important;
    border-radius: 0 !important;
    font-size: 13px !important;
}

/* Text input label */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label {
    color: #7a5500 !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* Column gaps */
[data-testid="column"] { padding: 0 3px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #080808; }
::-webkit-scrollbar-thumb { background: #7a5500; }

/* Chat input */
[data-testid="stChatInput"] {
    background: #030300 !important;
    border: 1px solid #7a5500 !important;
    border-radius: 0 !important;
}
[data-testid="stChatInput"] textarea {
    background: #030300 !important;
    color: #e8e8e8 !important;
    font-size: 14px !important;
    border: none !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: #ffb000 !important; }

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #1a1a1a !important;
    background: #060606 !important;
    border-radius: 0 !important;
}
[data-testid="stExpander"] summary {
    color: #7a5500 !important;
    font-size: 12px !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 1px !important;
}

/* Progress bar */
.stProgress > div > div { background-color: #ffb000 !important; }
.stProgress { border-radius: 0 !important; }

/* Metric */
[data-testid="stMetric"] { background: #0a0800 !important; border: 1px solid #1a1a1a !important; padding: 6px 10px !important; }
[data-testid="stMetric"] label { color: #7a5500 !important; font-size: 11px !important; font-family: 'Share Tech Mono', monospace !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #ffb000 !important; font-size: 18px !important; font-family: 'Share Tech Mono', monospace !important; }

/* Divider */
hr { border-color: #1a1a1a !important; margin: 5px 0 !important; }

/* Spinner */
.stSpinner > div { border-top-color: #ffb000 !important; }

/* Alert / info */
.stAlert { border-radius: 0 !important; border: 1px solid #7a5500 !important; background: #0a0800 !important; color: #e8e8e8 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 13px !important; }

/* Success message */
.element-container .stSuccess { background: #030a03 !important; border: 1px solid #00ff41 !important; border-radius: 0 !important; color: #00ff41 !important; font-family: 'Share Tech Mono', monospace !important; font-size: 13px !important; }

/* ── Retro glow effects ── */
@keyframes amber-pulse {
    0%, 100% { text-shadow: 0 0 4px #ffb000, 0 0 11px #ffb00066, 0 0 19px #ffb00033; }
    50%      { text-shadow: 0 0 6px #ffb000, 0 0 16px #ffb00088, 0 0 28px #ffb00044; }
}
@keyframes blink-cursor {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0; }
}
@keyframes scanline-scroll {
    0%   { background-position: 0 0; }
    100% { background-position: 0 100%; }
}

/* Scanline overlay on entire app */
.block-container::after {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 9999;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.08) 2px,
        rgba(0,0,0,0.08) 4px
    );
    animation: scanline-scroll 8s linear infinite;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages"      not in st.session_state: st.session_state.messages      = []
if "repo_name"     not in st.session_state: st.session_state.repo_name     = None
if "last_route"    not in st.session_state: st.session_state.last_route    = []
if "last_score"    not in st.session_state: st.session_state.last_score    = 0.0
if "indexed_files" not in st.session_state: st.session_state.indexed_files = []
if "sys_status"    not in st.session_state: st.session_state.sys_status    = {
    "chroma": "IDLE", "groq": "IDLE", "embed": "IDLE", "indexer": "IDLE"
}

# ── Helper: render panel box ──────────────────────────────────────────────────
def panel(content: str, border_color: str = "#1e1e1e") -> str:
    return f"""
    <div style="border:1px solid {border_color};padding:8px;background:#060606;
                font-family:'Share Tech Mono',monospace;font-size:13px;
                line-height:1.5;margin-bottom:5px;">
        {content}
    </div>"""

def panel_title(label: str) -> str:
    return f'<div style="font-size:12px;color:#7a5500;border-bottom:1px solid #1a1a1a;padding-bottom:3px;margin-bottom:6px;letter-spacing:1px;">{label}</div>'

def ctx_label(label: str) -> str:
    return f'<div style="color:#7a5500;font-size:11px;letter-spacing:1px;margin-bottom:1px;margin-top:5px;">{label}</div>'

def ctx_val(val: str, color: str = "#e8e8e8", size: str = "12px") -> str:
    return f'<div style="color:{color};font-size:{size};line-height:1.5;">{val}</div>'

def divider() -> str:
    return '<div style="border-top:1px solid #1a1a1a;margin:5px 0;"></div>'

# ── Load logo as base64 ───────────────────────────────────────────────────────
logo_b64 = ""
try:
    with open("reposage.png", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
except FileNotFoundError:
    pass

# ── Header ────────────────────────────────────────────────────────────────────
now = datetime.now().strftime("%d-%m-%Y %H:%M")
logo_img = f'<img src="data:image/png;base64,{logo_b64}" style="height:75px;margin-right:20px;filter:drop-shadow(0 0 10px #00ff41) drop-shadow(0 0 20px #00ff4133);">' if logo_b64 else ""

st.markdown(f"""
<div style="background:#0a0800;border:1px solid #ffb000;padding:12px 24px;
            margin-bottom:6px;display:flex;justify-content:space-between;
            align-items:center;font-family:'Share Tech Mono',monospace;
            box-shadow:0 0 20px #ffb00033 inset, 0 0 6px #ffb00022;">
    <div style="display:flex;align-items:center;">
        {logo_img}
        <div>
            <div style="color:#ffb000;font-size:35px;letter-spacing:5px;font-weight:bold;
                        font-family:'Press Start 2P',monospace;
                        animation:amber-pulse 3s ease-in-out infinite;
                        text-shadow:0 0 8px #ffb000, 0 0 18px #ffb00088, 0 0 30px #ffb00044;
                        line-height:1.55;">
                RepoSage
            </div>
            <div style="color:#7a5500;font-size:12px;letter-spacing:2px;margin-top:6px;
                        font-family:'Share Tech Mono',monospace;">
                Repository Intelligence Engine | Powered by RAG
            </div>
        </div>
    </div>
    <div style="text-align:right;font-size:12px;line-height:2;font-family:'Share Tech Mono',monospace;">
        <div style="color:#ffb000;text-shadow:0 0 4px #ffb00066;">v1.0.0-alpha</div>
        <div style="color:#7a5500;">@TensorNaut/RepoSage</div>
        <div style="color:#00ff41;text-shadow:0 0 6px #00ff4166;animation:amber-pulse 4s ease-in-out infinite;">[ ● SYSTEM ONLINE ]</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Three-column layout ───────────────────────────────────────────────────────
left, center, right = st.columns([1.3, 3.5, 1.2])

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Repo input + system status
# ══════════════════════════════════════════════════════════════════════════════
with left:
    st.markdown(panel(
        panel_title("+-- REPOSITORY -------+") +
        '<div style="color:#7a5500;font-size:12px;margin-bottom:2px;">$ github_url</div>',
        "#1e1e1e"
    ), unsafe_allow_html=True)

    repo_url    = st.text_input("", placeholder="github.com/owner/repo", label_visibility="collapsed", key="repo_url")
    col1, col2  = st.columns(2)
    max_commits = col1.number_input("# commits", min_value=50, max_value=2000, value=200, step=50)
    max_issues  = col2.number_input("# issues",  min_value=0,  max_value=1000, value=100, step=50)

    index_btn = st.button("-> INDEX REPO", key="index_btn")

    if index_btn:
        if not repo_url.strip():
            st.markdown('<div style="color:#ff4444;font-size:12px;border:1px solid #ff4444;padding:4px;margin-top:4px;">ERROR: Enter a valid GitHub URL.</div>', unsafe_allow_html=True)
        else:
            try:
                owner, repo = repo_url.strip().rstrip("/").split("/")[-2:]
                st.session_state.sys_status["indexer"] = "RUNNING"

                prog  = st.progress(0)
                stati = st.empty()

                stati.markdown('<div style="color:#ffb000;font-size:12px;">Fetching README...</div>', unsafe_allow_html=True)
                client  = GitHubClient(owner=owner, repo=repo)
                readme  = client.get_readme()
                summary = generate_project_summary(readme, owner, repo)
                save_project_context(summary)
                prog.progress(15)

                stati.markdown('<div style="color:#ffb000;font-size:12px;">Cloning metadata...</div>', unsafe_allow_html=True)
                commits = client.get_commits(max_commits=int(max_commits))
                issues  = client.get_issues(max_issues=int(max_issues))
                files   = client.get_code_files()
                prog.progress(45)

                stati.markdown('<div style="color:#ffb000;font-size:12px;">Chunking context...</div>', unsafe_allow_html=True)
                cc = chunk_commits(commits)
                ic = chunk_issues(issues)
                fc = chunk_code_files(files)
                prog.progress(65)

                stati.markdown('<div style="color:#ffb000;font-size:12px;">Embedding + storing...</div>', unsafe_allow_html=True)
                store_chunks(cc, "commits")
                store_chunks(ic, "issues")
                store_chunks(fc, "code")
                prog.progress(100)

                st.session_state.repo_name     = f"{owner}/{repo}"
                st.session_state.indexed_files = list_indexed_files("code")
                st.session_state.sys_status    = {"chroma": "ACTIVE", "groq": "ONLINE", "embed": "LOADED", "indexer": "IDLE"}
                st.session_state.messages      = []

                prog.empty()
                stati.markdown(f'<div style="color:#00ff41;font-size:12px;border:1px solid #00ff41;padding:4px;">INDEXED: {owner}/{repo}<br>{len(cc)} commits | {len(ic)} issues | {len(fc)} code</div>', unsafe_allow_html=True)

            except Exception as e:
                st.session_state.sys_status["indexer"] = "ERROR"
                st.markdown(f'<div style="color:#ff4444;font-size:12px;border:1px solid #ff4444;padding:4px;margin-top:4px;">ERROR: {str(e)}</div>', unsafe_allow_html=True)

    # # Metrics
    # if st.session_state.repo_name:
    #     m1, m2, m3 = st.columns(3)
    #     m1.metric("CMTS", max_commits)
    #     m2.metric("ISSU", max_issues)
    #     m3.metric("FILE", len(st.session_state.indexed_files))

    # System Status
    ss = st.session_state.sys_status
    def status_dot(s):
        if s in ("ACTIVE", "ONLINE", "LOADED"): return f'<span style="color:#00ff41;">[ {s} ]</span>'
        if s == "RUNNING": return f'<span style="color:#ffb000;">[ {s} ]</span>'
        if s == "ERROR":   return f'<span style="color:#ff4444;">[ {s} ]</span>'
        return f'<span style="color:#3a3020;">[ {s} ]</span>'

    st.markdown(panel(
        panel_title("+-- SYSTEM -----------+") +
        f'<div style="font-size:12px;line-height:2;color:#7a5500;">' +
        f'| CHROMA &nbsp;{status_dot(ss["chroma"])}<br>' +
        f'| GROQ &nbsp;&nbsp;&nbsp;{status_dot(ss["groq"])}<br>' +
        f'| EMBED &nbsp;&nbsp;{status_dot(ss["embed"])}<br>' +
        f'| INDEXER {status_dot(ss["indexer"])}<br>' +
        f'+--------------------+</div>',
        "#1e1e1e"
    ), unsafe_allow_html=True)

    # Last query routing (collections)
    routes = st.session_state.last_route
    coll_rows = ""
    for name_c in [("CODE", "code"), ("COMMITS", "commits"), ("ISSUES", "issues")]:
        label, key = name_c
        if key in routes:
            coll_rows += f'| <span style="color:#00ff41;">{label}&nbsp;[ACTIVE]</span> |<br>'
        else:
            coll_rows += f'| <span style="color:#e8e8e8;">{label} [SKIP] &nbsp;</span> |<br>'

    coll_html = ctx_label("LAST QUERY CONTEXT") + f'''
    <div style="font-size:12px;line-height:1.9;color:#7a5500;">
    +-- COLLECTIONS ----+<br>
    {coll_rows}
    +------------------+
    </div>'''
    st.markdown(panel(coll_html, "#1e1e1e"), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CENTER COLUMN — Console + Chat (scrollable chat area)
# ══════════════════════════════════════════════════════════════════════════════
with center:
    # Console bar
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;font-size:12px;
                border:1px solid #1e1e1e;padding:5px 10px;background:#040400;
                letter-spacing:1px;font-family:'Share Tech Mono',monospace;margin-bottom:5px;">
        <span style="color:#7a5500;">+-- CONSOLE</span>
        <span style="color:#00ff41;">[ ● SESSION ACTIVE ]</span>
        <span style="color:#7a5500;">{now} --+</span>
    </div>
    """, unsafe_allow_html=True)

    # Scrollable chat container with fixed height
    chat_container = st.container(height=480)

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="border:1px solid #1a1a1a;padding:10px;color:#7a5500;font-size:14px;
                        line-height:2;background:#030300;margin-bottom:8px;
                        font-family:'Share Tech Mono',monospace;">
                <span style="color:#ffb000;">+--------------------------------------+</span><br>
                | REPOSAGE v1.0.0 // Repo Intelligence |<br>
                | Index a repo via left panel to begin.|<br>
                | Ask about codes, commits, or issues. |<br>
                | File  queries : "examine the main.py" |<br>
                <span style="color:#ffb000;">+--------------------------------------+</span>
            </div>
            """, unsafe_allow_html=True)

        messages = st.session_state.messages
        for i, msg in enumerate(messages):
            # Place anchor before the last user query so auto-scroll targets it
            if msg["role"] == "user" and i >= len(messages) - 2:
                st.markdown('<div id="latest-query"></div>', unsafe_allow_html=True)

            if msg["role"] == "user":
                st.markdown(f"""
                <div style="margin:8px 0 3px;font-size:14px;
                            font-family:'Share Tech Mono',monospace;">
                    <span style="color:#7a5500;">USER:$</span>
                    <span style="color:#00ff41;margin-left:6px;">{msg['content']}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                file_badge = ""
                if msg.get("file_mode"):
                    file_badge = f' <span style="color:#7a5500;font-size:12px;">[FILE MODE: {msg["file_mode"]}]</span>'

                content_text = msg["content"]
                src_html = ""
                if msg.get("sources"):
                    src_html = f'<div style="color:#7a5500;font-size:12px;margin-top:5px;">+-- src: {msg["sources"]} --+</div>'

                st.markdown(f"""
                <div style="margin:3px 0 10px;padding:8px 12px;
                            border-left:2px solid #ffb000;background:#0a0800;
                            font-family:'Share Tech Mono',monospace;">
                    <div style="color:#ffb000;font-size:12px;margin-bottom:4px;letter-spacing:1px;">
                        +-- REPOSAGE {file_badge} --+
                    </div>
                    <pre style="color:#e8e8e8;font-size:14px;line-height:1.7;
                                white-space:pre-wrap;word-wrap:break-word;
                                font-family:'Share Tech Mono',monospace;
                                margin:0;background:transparent;border:none;">{content_text}</pre>
                    {src_html}
                </div>
                """, unsafe_allow_html=True)

        # Auto-scroll to latest query
        if st.session_state.messages:
            components.html("""
            <script>
                function scrollToLatest() {
                    try {
                        const doc = window.parent.document;
                        const anchor = doc.getElementById('latest-query');
                        if (anchor) {
                            anchor.scrollIntoView({behavior: 'smooth', block: 'start'});
                        }
                    } catch(e) {}
                }
                setTimeout(scrollToLatest, 200);
                setTimeout(scrollToLatest, 500);
            </script>
            """, height=0)

    # Status bar
    routes_str = "+".join(st.session_state.last_route) if st.session_state.last_route else "---"
    repo_str   = st.session_state.repo_name or "NO REPO INDEXED"

    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;font-size:11px;
                padding:4px 8px;background:#030300;border:1px solid #1a1a1a;
                color:#7a5500;letter-spacing:1px;
                font-family:'Share Tech Mono',monospace;margin-top:4px;">
        <span>REPO: <span style="color:#ffb000;">{repo_str}</span></span>
        <span>COLS: <span style="color:#e8e8e8;">{routes_str}</span></span>
        <span>MODEL: <span style="color:#e8e8e8;">llama-3.3-70b</span></span>
        <span>STATUS: <span style="color:#00ff41;">{"Online"}</span></span>
    </div>
    """, unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("$ ask anything about the codebase...", key="chat_input"):
        if not st.session_state.repo_name:
            st.markdown('<div style="color:#ff4444;font-size:13px;border:1px solid #ff4444;padding:5px;font-family:\'Share Tech Mono\',monospace;">ERROR: No repository indexed. Index a repo first using the left panel.</div>', unsafe_allow_html=True)
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Detect file mode for badge
            file_mention = extract_file_mention(prompt)
            routes       = route_query(prompt)
            st.session_state.last_route = routes

            with st.spinner(""):
                response = ask(prompt)

            st.session_state.sys_status["groq"] = "ONLINE"

            # Build source citation from file mention or routes
            if file_mention:
                sources = f"[{file_mention}]"
            else:
                sources = " ".join(f"[{r.upper()}]" for r in routes)

            st.session_state.messages.append({
                "role":      "assistant",
                "content":   response,
                "file_mode": f"{file_mention} | chunks" if file_mention else None,
                "sources":   sources
            })

            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Context panel
# ══════════════════════════════════════════════════════════════════════════════
with right:
    project_ctx = load_project_context()

    ctx_html = panel_title("+-- CONTEXT ----------+")

    if project_ctx:
        name = project_ctx.get("project_name", "Unknown")
        repo = project_ctx.get("repo", "")
        desc = project_ctx.get("description", "")
        purp = project_ctx.get("purpose", "")
        tech = project_ctx.get("tech_stack", [])

        ctx_html += ctx_label("PROJECT")
        ctx_html += f'<div style="color:#ffb000;font-size:14px;">{name}</div>'

        ctx_html += ctx_label("REPO")
        ctx_html += f'<div style="color:#e8e8e8;font-size:11px;">{repo}</div>'

        ctx_html += divider()

        if desc:
            ctx_html += ctx_label("SUMMARY")
            ctx_html += ctx_val(desc[:350] + ("..." if len(desc) > 350 else ""))

        if purp:
            ctx_html += ctx_label("PURPOSE")
            ctx_html += ctx_val(purp[:350] + ("..." if len(purp) > 350 else ""))

        ctx_html += divider()

        if tech:
            ctx_html += ctx_label("TECH STACK")
            tags = "".join(
                f'<span style="border:1px solid #ffb000;padding:1px 4px;font-size:11px;display:inline-block;margin:1px;color:#ffb000;">{t}</span>'
                for t in tech
            )
            ctx_html += f'<div style="margin-top:2px;">{tags}</div>'

        ctx_html += divider()

    else:
        ctx_html += '<div style="color:#3a3020;font-size:12px;line-height:2;">No context loaded.<br>Index a repository<br>to populate this panel.</div>'

    st.markdown(panel(ctx_html, "#1e1e1e"), unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;justify-content:space-between;font-size:13px;
            color:#3a2a10;margin-top:4px;padding:0 2px;letter-spacing:1px;
            font-family:'Share Tech Mono',monospace;">
    <span>+-- REPOSAGE v1.0.0-alpha</span>
    <span>ChromaDB + SentenceTransformers + Groq</span>
    <span>@TensorNaut/RepoSage --+</span>
</div>
""", unsafe_allow_html=True)