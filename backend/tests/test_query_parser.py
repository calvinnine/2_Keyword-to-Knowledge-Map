"""Tests for natural-language → keyword parsing."""

from datetime import datetime

import pytest

from app.nlp.query_parser import HeuristicQueryParser


@pytest.fixture
def parser():
    return HeuristicQueryParser()


class TestKeywordExtraction:
    def test_korean_who_question(self, parser):
        """Example from spec: 'quantum computing 분야에서 누가 잘해?'"""
        p = parser.parse("quantum computing 분야에서 누가 잘해?")
        assert p.keyword == "quantum computing"
        assert p.intent == "author_influence"
        assert p.year_start is None
        assert p.year_end is None

    def test_english_topic_question(self, parser):
        p = parser.parse("Who are the top researchers in foundation models?")
        assert "foundation models" in p.keyword.lower()
        assert p.intent == "author_influence"

    def test_paper_intent(self, parser):
        p = parser.parse("digital twin 분야에서 어떤 논문이 중요해?")
        assert "digital twin" in p.keyword
        assert p.intent == "paper_centrality"

    def test_keyword_clusters_intent(self, parser):
        p = parser.parse("AI governance 분야의 동향이 궁금해")
        assert "AI governance" in p.keyword or "ai governance" in p.keyword.lower()
        assert p.intent == "keyword_clusters"

    def test_plain_keyword_passes_through(self, parser):
        p = parser.parse("graph neural network")
        assert p.keyword == "graph neural network"
        assert p.intent == "general"


class TestYearExtraction:
    def test_recent_years_korean(self, parser):
        p = parser.parse("최근 5년 동안 quantum computing 분야에서 누가 잘해?")
        assert p.keyword == "quantum computing"
        assert p.intent == "author_influence"
        current_year = datetime.now().year
        assert p.year_end == current_year
        assert p.year_start == current_year - 4

    def test_recent_years_english(self, parser):
        p = parser.parse("Top authors in scientific discovery in recent 3 years")
        assert "scientific discovery" in p.keyword.lower()
        current_year = datetime.now().year
        assert p.year_end == current_year
        assert p.year_start == current_year - 2

    def test_explicit_year_range(self, parser):
        p = parser.parse("foundation model 2018-2023 분야에서 핵심 논문")
        assert "foundation model" in p.keyword
        assert p.year_start == 2018
        assert p.year_end == 2023

    def test_single_year(self, parser):
        p = parser.parse("AI safety in 2024")
        assert p.year_start == 2024
        assert p.year_end == 2024


class TestEdgeCases:
    def test_empty_input(self, parser):
        p = parser.parse("")
        assert p.keyword == ""
        assert p.intent == "general"

    def test_whitespace_only(self, parser):
        p = parser.parse("   ")
        assert p.keyword == ""

    def test_only_question_words(self, parser):
        """A query with no extractable keyword yields an empty string so the
        API layer can reject it (422). Intent is still detected.
        """
        p = parser.parse("누가 잘해?")
        assert p.keyword == ""
        assert p.intent == "author_influence"

    def test_to_params_carries_original(self, parser):
        p = parser.parse("quantum computing 분야에서 누가 잘해?")
        params = p.to_params()
        assert params["source"] == "nl_query"
        assert params["original_query"] == "quantum computing 분야에서 누가 잘해?"
        assert params["intent"] == "author_influence"

    def test_punctuation_stripped(self, parser):
        p = parser.parse("digital twin?")
        assert p.keyword == "digital twin"
