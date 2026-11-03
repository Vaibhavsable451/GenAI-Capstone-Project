"""
Career Copilot - GenAI Capstone
LLM API (Groq gpt-oss-120b) + Prompt Engineering + RAG (ChromaDB) + Tools + Agent loop
"""
import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError

from copilot.agent import run_agent
from copilot.ats import ats_match
from copilot.llm import MODEL, chat, get_client
from copilot.prompts import ATS_SYSTEM, MODES
from copilot.tools import STATUSES, TOOL_SPECS, ToolBox
from copilot.vectorstore import VectorStore

load_dotenv()
st.set_page_config(page_title="Career Copilot", page_icon="🚀", layout="wide")


def configured_key() -> str | None:
    """Key from environment (.env) or Streamlit Cloud secrets."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except Exception:
            key = None
    return key


def get_api_key() -> str | None:
    return configured_key() or st.session_state.get("manual_key")


@st.cache_resource
def get_store() -> VectorStore:
    return VectorStore()


store = get_store()
toolbox = ToolBox(store)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("tokens", 0)

# ================= Sidebar =================
with st.sidebar:
    st.title("🚀 Career Copilot")
    if not configured_key():
        st.text_input("Groq API key", type="password", key="manual_key")
    st.caption(f"Model: `{MODEL}`")

    mode = st.selectbox("Assistant mode", list(MODES))
    temperature = st.slider("Temperature", 0.0, 1.0, MODES[mode]["temperature"], 0.1)
    max_steps = st.slider("Max agent steps", 1, 10, 6)
    enabled = set(st.multiselect("Enabled tools", list(TOOL_SPECS), default=list(TOOL_SPECS)))
    allow_destructive = st.toggle("Allow destructive actions (delete_job)", value=False)

    st.divider()
    st.metric("Tokens used", st.session_state.tokens)
    st.caption(f"📚 {store.count()} chunks indexed")
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages, st.session_state.tokens = [], 0
        st.rerun()


def render_trace(trace):
    for ev in trace:
        if ev["type"] == "tool_call":
            st.markdown(f"🔧 **Call** `{ev['name']}` `{json.dumps(ev['args'])[:300]}`")
        else:
            st.markdown(f"📥 **Result:** {ev['result'][:600]}")


st.title("🚀 Career Copilot")
st.caption("Your AI career assistant · LLM + Prompt Engineering + RAG + Tools + Agent")

tab_chat, tab_docs, tab_ats, tab_jobs, tab_about = st.tabs(
    ["💬 Copilot", "📄 Documents", "📊 ATS Match", "🗂️ Job Tracker", "ℹ️ About"])

# ================= Documents (RAG ingestion) =================
with tab_docs:
    st.subheader("Upload your resume, job descriptions and notes")
    files = st.file_uploader("PDF / DOCX / TXT / MD", type=["pdf", "docx", "txt", "md"],
                             accept_multiple_files=True)
    c1, c2 = st.columns(2)
    chunk_size = c1.slider("Chunk size (chars)", 300, 2000, 800, 100)
    overlap = c2.slider("Chunk overlap (chars)", 0, 400, 120, 20)

    b1, b2, b3 = st.columns(3)
    if b1.button("⚙️ Process uploads", disabled=not files, use_container_width=True):
        with st.spinner("Chunking and embedding (first run downloads the embedding model)..."):
            for f in files:
                try:
                    n = store.add_file(f.name, f.getvalue(), chunk_size, overlap)
                    st.success(f"{f.name}: {n} chunks" if n else f"{f.name}: already indexed")
                except Exception as e:
                    st.error(f"{f.name}: {e}")
    if b2.button("🎯 Load sample resume + JD", use_container_width=True):
        with st.spinner("Indexing sample data..."):
            for p in sorted(Path("sample_data").glob("*.txt")):
                store.add_file(p.name, p.read_bytes(), chunk_size, overlap)
        st.success("Sample data loaded.")
    if b3.button("💣 Reset index", use_container_width=True):
        store.reset()
        st.rerun()

    st.markdown("**Indexed documents:** " + (", ".join(f"`{s}`" for s in store.sources()) or "none yet"))

# ================= Chat (agent) =================
with tab_chat:
    st.info(f"Mode: **{mode}** · try: *Review my resume against the Junior AI Engineer JD* "
            "or *Add Google – ML Intern to my tracker as Applied*")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m.get("trace"):
                with st.expander(f"🧠 Agent steps ({sum(e['type'] == 'tool_call' for e in m['trace'])} tool calls)"):
                    render_trace(m["trace"])
            st.markdown(m["content"])

    if task := st.chat_input("Ask Career Copilot..."):
        key = get_api_key()
        if not key:
            st.error("Add GROQ_API_KEY to .env / Streamlit secrets, or enter it in the sidebar.")
            st.stop()
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": task})
        with st.chat_message("user"):
            st.markdown(task)
        with st.chat_message("assistant"):
            trace, final = [], None
            try:
                with st.status("Agent working...", expanded=True) as status:
                    for ev in run_agent(get_client(key), toolbox, mode, history, task, enabled,
                                        allow_destructive, max_steps, temperature):
                        if ev["type"] == "final":
                            final = ev
                        else:
                            trace.append(ev)
                            render_trace([ev])
                    status.update(label=f"Done in {final['steps']} step(s)", state="complete", expanded=False)
                st.session_state.tokens += final["tokens"]
                st.session_state.messages.append({"role": "assistant", "content": final["content"], "trace": trace})
                st.rerun()
            except AuthenticationError:
                st.error("🔑 Invalid API key.")
            except RateLimitError:
                st.error("⏳ Rate limit reached. Try again shortly.")
            except APIConnectionError:
                st.error("🌐 Network problem reaching Groq.")
            except APIStatusError as e:
                st.error(f"API error {e.status_code}: {e.message}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

# ================= ATS Match (rule-based + structured LLM JSON) =================
with tab_ats:
    st.subheader("Resume ↔ Job Description match")
    sources = store.sources()
    if not sources:
        st.warning("Index your resume first (Documents tab) — or load the sample data.")
    else:
        resume_src = st.selectbox("Resume document", sources)
        jd_default = Path("sample_data/sample_jd.txt").read_text() if "sample_jd.txt" in sources else ""
        jd = st.text_area("Paste the job description", value=jd_default, height=220)
        if st.button("Analyse match", type="primary", disabled=not jd.strip()):
            resume_text = store.get_text(resume_src)
            r = ats_match(jd, resume_text)
            m1, m2, m3 = st.columns(3)
            m1.metric("ATS keyword score", f"{r['score']}%")
            m2.metric("Matched", len(r["matched"]))
            m3.metric("Missing", len(r["missing"]))
            st.progress(r["score"] / 100)
            st.markdown("✅ **Matched:** " + (", ".join(f"`{k}`" for k in r["matched"]) or "—"))
            st.markdown("❌ **Missing:** " + (", ".join(f"`{k}`" for k in r["missing"]) or "—"))

            key = get_api_key()
            if key:
                try:
                    with st.spinner("AI analysis (structured JSON)..."):
                        resp = chat(get_client(key), [
                            {"role": "system", "content": ATS_SYSTEM},
                            {"role": "user", "content": f"RESUME:\n{resume_text[:6000]}\n\nJOB DESCRIPTION:\n{jd[:4000]}\n\n"
                                                        f"KEYWORD STATS: {json.dumps(r)}"}],
                            temperature=0.2, json_mode=True)
                    st.session_state.tokens += resp.usage.total_tokens
                    data = json.loads(resp.choices[0].message.content)
                    st.markdown(f"### Summary\n{data.get('summary', '')}")
                    cols = st.columns(2)
                    cols[0].markdown("### 💪 Strengths\n" + "\n".join(f"- {x}" for x in data.get("strengths", [])))
                    cols[1].markdown("### 🧩 Gaps\n" + "\n".join(f"- {x}" for x in data.get("gaps", [])))
                    st.markdown("### ✍️ Suggested bullets\n" + "\n".join(f"- {x}" for x in data.get("suggested_bullets", [])))
                    st.markdown("### 🎯 Next steps\n" + "\n".join(f"- {x}" for x in data.get("next_steps", [])))
                except json.JSONDecodeError:
                    st.warning("The model did not return valid JSON. Try again.")
                except (AuthenticationError, RateLimitError, APIConnectionError, APIStatusError) as e:
                    st.error(f"LLM error: {e}")
            else:
                st.caption("Add a Groq key to get the AI written analysis.")

# ================= Job tracker =================
with tab_jobs:
    st.subheader("Application tracker")
    st.caption("The agent can also manage this via chat (e.g. “mark job 2 as Interview”).")
    with st.form("add_job", clear_on_submit=True):
        a, b, c = st.columns(3)
        company, role = a.text_input("Company"), b.text_input("Role")
        status = c.selectbox("Status", STATUSES)
        notes = st.text_input("Notes")
        if st.form_submit_button("Add job") and company and role:
            toolbox.add_job(company, role, status, notes)
            st.rerun()
    rows = toolbox.rows()
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        d1, d2 = st.columns([3, 1])
        del_id = d1.selectbox("Delete job id", [r["id"] for r in rows])
        if d2.button("Delete", use_container_width=True):
            toolbox.delete_job(del_id)
            st.rerun()
    else:
        st.info("No jobs yet.")

# ================= About =================
with tab_about:
    st.subheader("How it works")
    img = Path("docs/architecture.png")
    if img.exists():
        st.image(str(img), caption="System architecture")
    st.markdown("""
| Capstone requirement | Implementation |
|---|---|
| LLM API | Groq `openai/gpt-oss-120b`, retries, JSON mode |
| Prompt engineering | Role prompts, assistant modes, few-shot STAR feedback, constraints, JSON schema |
| RAG | Loader → chunker → MiniLM embeddings → ChromaDB → semantic search |
| Tools | Document search, ATS match, job tracker (SQLite), company lookup, time |
| Agent | Understand → Decide → Use Tool → Process Result → Respond, step limit, destructive-action guard |
""")
