"""BM25 keyword retrieval in pure Python (no vector database or GPU needed).

BM25 is the ranking function behind classic search engines. For company documents
(policies, contracts, FAQs) it works very well and is fully explainable.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from docassist.documents import Chunk

STOPWORDS = set("""
a an and are as at be by for from has have how i in is it its of on or that the this to was were what when
where which who why will with do does can my our your you we they there their about after before
el la los las un una unos unas y o de del en que es son por para con como se su sus al lo cuando cual
cuales donde quien porque mi tu nuestro nuestra hay qué cómo cuándo dónde cuál
""".split())


def tokenize(text: str) -> list[str]:
    """Lowercase, strip accents, drop EN/ES stopwords and lightly stem the remaining words."""
    text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [_stem(t) for t in tokens if t not in STOPWORDS and len(t) > 1]


def _stem(token: str) -> str:
    """Very light stemming so 'refunds' matches 'refund' and 'policies' matches 'policy'."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    for suffix in ("ing", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


class BM25Index:
    """Keyword index over chunks, ranked with the BM25 formula."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        df = Counter(term for doc in self.docs for term in doc)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        """Return up to `top_k` (chunk, score) pairs with a positive score, best first."""
        terms = tokenize(query)
        scored = []
        for chunk, doc, length in zip(self.chunks, self.docs, self.lengths):
            score = 0.0
            for term in terms:
                if term not in doc:
                    continue
                tf = doc[term]
                score += self.idf[term] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
