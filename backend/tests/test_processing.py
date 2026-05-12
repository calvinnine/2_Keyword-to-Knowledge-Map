"""Unit tests for the processing module — pure functions, no DB required."""

from app.processing.normalizer import (
    normalize_doi,
    normalize_title,
    normalize_keyword,
    normalize_author_name,
    decode_inverted_abstract,
)
from app.processing.dedup import PaperDeduplicator
from app.processing.affiliation import extract_country, extract_openalex_affiliation


class TestNormalizer:
    def test_doi_strip_url_and_lowercase(self):
        assert normalize_doi("https://doi.org/10.1234/ABC") == "10.1234/abc"
        assert normalize_doi("https://dx.doi.org/10.5/X") == "10.5/x"
        assert normalize_doi("  10.1/foo  ") == "10.1/foo"

    def test_doi_none(self):
        assert normalize_doi(None) is None
        assert normalize_doi("") is None

    def test_title_normalize(self):
        a = normalize_title("Foundation Models: A Survey!")
        b = normalize_title("foundation models a survey")
        assert a == b == "foundation models a survey"

    def test_title_unicode(self):
        # Unicode → ASCII normalization
        assert normalize_title("Café Études") == "cafe etudes"

    def test_keyword_normalize(self):
        assert normalize_keyword("  Digital Twin ") == "digital twin"
        assert normalize_keyword(None) is None

    def test_author_name_collapse_whitespace(self):
        assert normalize_author_name("  John   Doe  ") == "John Doe"

    def test_decode_inverted_abstract(self):
        inverted = {"hello": [0, 3], "world": [1], "foo": [2]}
        # positions: 0=hello, 1=world, 2=foo, 3=hello
        assert decode_inverted_abstract(inverted) == "hello world foo hello"

    def test_decode_inverted_empty(self):
        assert decode_inverted_abstract(None) is None
        assert decode_inverted_abstract({}) is None


class TestDeduplicator:
    def test_doi_priority(self):
        d = PaperDeduplicator()
        assert d.check_and_register("10.1/a", "some title") is False
        # Same DOI → duplicate even if title differs
        assert d.check_and_register("10.1/a", "different title") is True

    def test_title_fallback(self):
        d = PaperDeduplicator()
        assert d.check_and_register(None, "title fingerprint") is False
        assert d.check_and_register(None, "title fingerprint") is True

    def test_no_doi_no_title_never_dup(self):
        d = PaperDeduplicator()
        assert d.check_and_register(None, None) is False
        assert d.check_and_register(None, None) is False


class TestAffiliation:
    def test_extract_country_from_openalex_institution(self):
        inst = {"country_code": "us", "display_name": "MIT", "country": "United States"}
        cc, cn = extract_country(inst)
        assert cc == "US"
        assert cn == "United States"

    def test_extract_country_empty(self):
        assert extract_country(None) == (None, None)
        assert extract_country({}) == (None, None)

    def test_extract_openalex_affiliation_multi(self):
        authorship = {
            "raw_affiliation_strings": ["MIT, USA"],
            "institutions": [
                {"id": "I1", "display_name": "MIT", "country_code": "US", "ror": "ror1"},
                {"id": "I2", "display_name": "Harvard", "country_code": "US"},
            ],
        }
        result = extract_openalex_affiliation(authorship)
        assert len(result) == 2
        assert result[0]["institution_openalex_id"] == "I1"
        assert result[0]["country_code"] == "US"
        assert result[0]["ror_id"] == "ror1"
        assert result[1]["institution_name"] == "Harvard"
