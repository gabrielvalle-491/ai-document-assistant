"""Web interface: upload documents -> ask questions -> get answers with sources.

    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from docassist.answer import ask, provider
from docassist.documents import load_documents
from docassist.retrieval import BM25Index

SAMPLES = Path(__file__).parent / "samples"

st.set_page_config(page_title="AI Document Assistant", page_icon="📄", layout="wide")
st.title("📄 AI Document Assistant")
st.caption("Upload documents → ask questions → get answers with the exact source.")

with st.sidebar:
    st.header("Documents")
    uploads = st.file_uploader("PDF, TXT or Markdown", type=["pdf", "txt", "md"], accept_multiple_files=True)
    use_samples = st.checkbox("Use sample company documents", value=not uploads)
    use_llm = st.toggle("Use AI to write the answer", value=provider() is not None, disabled=provider() is None)
    st.caption(f"AI provider: **{provider() or 'none (set ANTHROPIC_API_KEY or GEMINI_API_KEY)'}**")


@st.cache_resource(show_spinner="Indexing documents…")
def build_index(files: tuple[tuple[str, bytes], ...]) -> BM25Index:
    return BM25Index(load_documents(list(files)))


files = [(f.name, f.getvalue()) for f in uploads or []]
if use_samples and SAMPLES.exists():
    files += [(p.name, p.read_bytes()) for p in sorted(SAMPLES.glob("*.pdf"))]

if not files:
    st.info("Upload at least one document or enable the sample documents in the sidebar.")
    st.stop()

index = build_index(tuple(files))
st.success(f"{len(index.chunks)} passages indexed from {len(files)} documents.")

examples = ["How many vacation days do employees get?", "What is the refund policy?",
            "What happens if uptime is below 99.5%?"]
cols = st.columns(len(examples))
for col, example in zip(cols, examples):
    if col.button(example, use_container_width=True):
        st.session_state["question"] = example

question = st.text_input("Your question", key="question")
if question:
    result = ask(index, question, use_llm=use_llm)
    st.markdown(f"### Answer\n{result.text}")
    st.caption(f"Mode: {result.mode}")
    st.markdown("#### Sources")
    for number, chunk, score in result.sources:
        with st.expander(f"[{number}] {chunk.citation} — relevance {score:.2f}"):
            st.write(chunk.text)
