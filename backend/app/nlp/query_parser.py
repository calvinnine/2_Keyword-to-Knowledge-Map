"""Natural-language query → structured job parameters.

The planning report mandates that the analysis core operates on a *keyword*,
not on a natural-language question. This module is a thin translation layer:

  raw NL query  ──parser──►  { keyword, intent, year_start, year_end }
                                  │
                                  ▼
                              existing keyword-based pipeline

The parser is deliberately heuristic and deterministic so the same input
always yields the same job. An LLM-backed parser can be plugged in later by
implementing the same `parse()` interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

Intent = Literal[
    "author_influence",   # "누가 잘해?", "who is leading"
    "paper_centrality",   # "주요 논문", "key papers"
    "keyword_clusters",   # "어떤 주제들?", "trends", "동향"
    "general",            # no specific intent detected
]


@dataclass
class ParsedQuery:
    keyword: str
    intent: Intent
    year_start: int | None
    year_end: int | None
    raw_query: str

    def to_params(self) -> dict:
        """Subset suitable for storing on AnalysisJob.params."""
        return {
            "source": "nl_query",
            "original_query": self.raw_query,
            "intent": self.intent,
        }


class QueryParser(Protocol):
    def parse(self, query: str) -> ParsedQuery: ...


# ---------------------------------------------------------------------------
# Pattern dictionaries
# ---------------------------------------------------------------------------

# Order matters only for documentation — detection picks the first intent
# whose keywords match.
_INTENT_PATTERNS: dict[Intent, tuple[str, ...]] = {
    "author_influence": (
        "누가", "누구", "연구자", "저자", "전문가", "권위자", "스타 연구자",
        "who", "researcher", "researchers", "author", "authors", "scientist",
    ),
    "paper_centrality": (
        "논문", "페이퍼", "대표 연구", "핵심 연구", "주요 연구",
        "paper", "papers", "study", "studies", "publication", "publications",
    ),
    "keyword_clusters": (
        "주제", "토픽", "동향", "트렌드", "흐름", "분야 구조", "구조",
        "topic", "topics", "trend", "trends", "subfield", "subfields", "landscape",
    ),
}

# Phrases to strip when isolating the keyword. Sorted descending by length
# at use-time so multi-word phrases are removed before their substrings.
_STOPWORDS_KO: tuple[str, ...] = (
    # locational / scoping particles
    "분야에서", "분야의", "분야", "영역에서", "영역의", "영역",
    "쪽에서", "쪽의", "쪽",
    "에 관한", "에 대한", "에 대해", "에서", "에서의", "관련된", "관련",
    # question / interrogatives
    "누가", "누구", "어떤", "어느", "뭐가", "무엇이", "무엇", "뭐", "어디가", "어디",
    # qualifying adjectives
    "최고", "대표", "주요", "주된", "핵심", "유력한", "유명한",
    # predicates / sentence enders
    "잘해", "잘하나", "잘하는지", "잘하고",
    "유명해", "유명한지", "핫해", "핫한지", "중요해", "중요한지",
    "있나", "있어", "있을까", "되나", "되는지",
    "궁금해", "궁금한지", "궁금하다", "알고 싶어", "알고싶어", "보고 싶어", "보고싶어",
    "핫한", "핫", "괜찮은", "괜찮아", "좋은",
    # connectives
    "관련해서", "관련해", "해서", "에 관해서", "에 관해",
    # imperatives
    "알려줘", "보여줘", "찾아줘", "분석해줘", "비교해줘", "정리해줘", "추천해줘",
    # time adverbs (year extraction handled separately)
    "최근", "요즘", "근래", "동안", "기간",
    # nouns also used as intent triggers — safe to strip after intent detection
    "논문", "페이퍼", "연구자", "저자", "전문가", "권위자", "스타 연구자",
    "주제", "토픽", "동향", "트렌드", "흐름", "분야 구조", "구조",
)

_STOPWORDS_EN: tuple[str, ...] = (
    # interrogatives
    "who", "what", "which", "where", "when", "how",
    # articles / common verbs
    "is", "are", "was", "were", "the", "a", "an", "do", "does",
    # qualifiers
    "best", "top", "leading", "influential", "important", "key", "major",
    # prepositions
    "in", "of", "on", "for", "about", "around", "with",
    # scope nouns
    "field", "fields", "area", "areas", "domain", "domains",
    "topic", "topics", "subject",
    "researchers", "researcher", "authors", "author", "papers", "paper",
    # imperatives
    "show", "find", "analyze", "compare", "tell", "list",
    # adverbs
    "recently", "lately",
)

# Korean postpositional particles. Filtered as standalone tokens after
# stopword stripping (Python's `re` doesn't support variable-width lookbehind,
# so we split-and-filter rather than regex-substitute).
_KO_PARTICLES: frozenset[str] = frozenset({
    "이", "가", "은", "는", "을", "를", "의", "에", "와", "과",
    "로", "으로", "도", "만", "랑", "이랑",
})

# Year patterns
_YEAR_RECENT = re.compile(
    r"최근\s*(\d+)\s*년|지난\s*(\d+)\s*년|recent\s+(\d+)\s+years?",
    re.IGNORECASE,
)
_YEAR_RANGE = re.compile(r"(\d{4})\s*[-~–]\s*(\d{4})")
_YEAR_SINGLE = re.compile(r"\b(19\d{2}|20\d{2})\s*년?\b")


# ---------------------------------------------------------------------------
# Heuristic parser
# ---------------------------------------------------------------------------


class HeuristicQueryParser:
    """Rule-based parser. Deterministic and dependency-free."""

    def parse(self, query: str) -> ParsedQuery:
        raw = (query or "").strip()
        if not raw:
            return ParsedQuery(
                keyword="", intent="general",
                year_start=None, year_end=None, raw_query=raw,
            )

        text = raw
        # Detect intent against the original text (before stripping)
        intent = self._detect_intent(text)

        # Year extraction
        year_start, year_end, text = self._extract_years(text)

        # Strip trailing question/end punctuation
        text = re.sub(r"[?!.。？！]+$", "", text).strip()

        # Strip stopword phrases (longest first)
        all_stopwords = sorted(
            _STOPWORDS_KO + _STOPWORDS_EN, key=len, reverse=True
        )
        for sw in all_stopwords:
            pattern = re.compile(
                rf"(?<![A-Za-z0-9_]){re.escape(sw)}(?![A-Za-z0-9_])",
                flags=re.IGNORECASE,
            )
            text = pattern.sub(" ", text)

        # Drop isolated Korean particle tokens left over after stopword removal
        tokens = [tok for tok in text.split() if tok not in _KO_PARTICLES]
        text = " ".join(tokens)

        # Collapse whitespace and trim leading/trailing punctuation
        text = re.sub(r"\s+", " ", text).strip(" ,.;:-_/")

        # Intentionally no fallback: if every token was stopword-like, the
        # query carried no extractable keyword and the API will reject with 422.

        return ParsedQuery(
            keyword=text,
            intent=intent,
            year_start=year_start,
            year_end=year_end,
            raw_query=raw,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _detect_intent(text: str) -> Intent:
        lowered = text.lower()
        for intent, kws in _INTENT_PATTERNS.items():
            for kw in kws:
                # Word-boundary-aware match for ASCII; substring for Hangul
                if kw.isascii():
                    if re.search(rf"\b{re.escape(kw)}\b", lowered):
                        return intent
                else:
                    if kw in lowered:
                        return intent
        return "general"

    @staticmethod
    def _extract_years(text: str) -> tuple[int | None, int | None, str]:
        m = _YEAR_RECENT.search(text)
        if m:
            n_str = m.group(1) or m.group(2) or m.group(3)
            n = int(n_str)
            year_end = datetime.now().year
            year_start = year_end - n + 1
            text = _YEAR_RECENT.sub(" ", text)
            return year_start, year_end, text

        m = _YEAR_RANGE.search(text)
        if m:
            ys, ye = int(m.group(1)), int(m.group(2))
            text = _YEAR_RANGE.sub(" ", text)
            if ys > ye:
                ys, ye = ye, ys
            return ys, ye, text

        # Single year mentioned → treat as both start and end
        m = _YEAR_SINGLE.search(text)
        if m:
            y = int(m.group(1))
            text = _YEAR_SINGLE.sub(" ", text)
            return y, y, text

        return None, None, text
