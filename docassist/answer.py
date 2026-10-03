"""Turn retrieved chunks into an answer with citations.

- With an API key (Claude or Gemini) the LLM writes the answer, constrained to the
  retrieved context and forced to cite sources like [1], [2].
- Without a key, an extractive fallback returns the most relevant sentences verbatim,
  so the tool still works offline and never invents anything.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

from docassist.documents import Chunk
from docassist.retrieval import BM25Index, tokenize

NOT_FOUND = "I couldn't find this in the uploaded documents."

SYSTEM = (
    "You answer questions using ONLY the numbered context passages. Cite every fact with the passage "
    "number in brackets, e.g. [1]. If the answer is not in the context, reply exactly: "
    f'"{NOT_FOUND}" Answer in the same language as the question. Be concise.'
)


@dataclass
class Answer:
    """An answer plus the numbered sources it was built from."""

    text: str
    sources: list[tuple[int, Chunk, float]]
    mode: str  # "claude", "gemini" or "extractive"


def build_prompt(question: str, hits: list[tuple[Chunk, float]]) -> str:
    """Build the user prompt: numbered context passages (with citations) followed by the question."""
    context = "\n\n".join(f"[{i}] ({chunk.citation})\n{chunk.text}" for i, (chunk, _) in enumerate(hits, start=1))
    return f"Context passages:\n{context}\n\nQuestion: {question}"


def provider() -> str | None:
    """Return the configured AI provider ("claude" or "gemini"), or None if no API key is set."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return None


def call_llm(prompt: str, which: str, system: str = SYSTEM) -> str:
    """Send `prompt` to Claude or Gemini and return the reply text (raises on HTTP errors)."""
    if which == "claude":
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages", timeout=60,
            headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
            json={"model": os.environ.get("LLM_MODEL", "claude-haiku-4-5"), "max_tokens": 600, "system": system,
                  "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
    resp = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", timeout=60,
        headers={"Authorization": f"Bearer {os.environ['GEMINI_API_KEY']}"},
        json={"model": os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite"),
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def sentences(chunk_text: str) -> list[str]:
    """Chunks store one unit per line; headings (no final punctuation) are not answers."""
    return [u for u in chunk_text.split("\n") if u.endswith((".", "!", "?"))]


def extractive_answer(question: str, hits: list[tuple[Chunk, float]], max_sentences: int = 2) -> str:
    """Pick the sentences that share the most terms with the question, and cite them."""
    q_terms = set(tokenize(question))
    candidates = []
    for i, (chunk, _) in enumerate(hits, start=1):
        for sentence in sentences(chunk.text):
            overlap = len(q_terms & set(tokenize(sentence)))
            if overlap:
                candidates.append((overlap, -i, sentence.strip(), i))
    if not candidates:
        return NOT_FOUND
    candidates.sort(reverse=True)
    best = sorted(candidates[:max_sentences], key=lambda c: -c[1])
    return " ".join(f"{sentence} [{i}]" for _, _, sentence, i in best)


def expand_query(question: str, which: str) -> str:
    """Let the LLM rewrite the question as keywords in English and Spanish (cross-language search)."""
    prompt = ("Rewrite this question as a short list of search keywords, in English AND Spanish, including "
              f"synonyms. Reply with the keywords only.\n\nQuestion: {question}")
    try:
        return f"{question} {call_llm(prompt, which, system='You generate search keywords.')}"
    except Exception:
        return question


def ask(index: BM25Index, question: str, top_k: int = 4, use_llm: bool = True) -> Answer:
    """Retrieve the best passages for `question` and answer with an LLM or the extractive fallback."""
    which = provider() if use_llm else None
    query = expand_query(question, which) if which else question
    hits = index.search(query, top_k=top_k)
    sources = [(i, chunk, score) for i, (chunk, score) in enumerate(hits, start=1)]
    if not hits:
        return Answer(NOT_FOUND, [], "extractive")
    if which:
        try:
            return Answer(call_llm(build_prompt(question, hits), which), sources, which)
        except Exception as exc:  # network/quota problems degrade gracefully
            text = extractive_answer(question, hits)
            return Answer(f"{text}\n\n(LLM unavailable: {exc.__class__.__name__}; showing extractive answer)",
                          sources, "extractive")
    return Answer(extractive_answer(question, hits), sources, "extractive")
