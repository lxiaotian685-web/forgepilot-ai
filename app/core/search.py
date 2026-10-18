from __future__ import annotations

import math
import re

_ASCII_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = list(_ASCII_RE.findall(text))
    for run in _CJK_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


class BM25Index:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.tokenized = [tokenize(doc) for doc in corpus]
        self.avgdl = sum(len(t) for t in self.tokenized) / max(len(corpus), 1)
        self.doc_freq: dict[str, int] = self._build_doc_freq()

    def _build_doc_freq(self) -> dict[str, int]:
        doc_freq: dict[str, int] = {}
        for tokens in self.tokenized:
            for term in set(tokens):
                doc_freq[term] = doc_freq.get(term, 0) + 1
        return doc_freq

    def _idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        if df == 0:
            return 0.0
        return math.log((len(self.corpus) - df + 0.5) / (df + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        query_tokens = tokenize(query)
        scores = [0.0] * len(self.corpus)
        for term in query_tokens:
            idf = self._idf(term)
            if idf == 0.0:
                continue
            for i, tokens in enumerate(self.tokenized):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                length = len(tokens) or 1
                denom = tf + self.k1 * (1 - self.b + self.b * length / max(self.avgdl, 1))
                scores[i] += idf * (tf * (self.k1 + 1)) / denom

        ranked = sorted(
            ((i, score) for i, score in enumerate(scores) if score > 0),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:top_k]
