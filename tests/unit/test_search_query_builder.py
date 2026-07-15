"""Unit tests for query builders."""

import pytest

from src.search.query_builder import (
    DomainQueryBuilder,
    KeywordQueryBuilder,
    PhraseQueryBuilder,
)
from src.search.exceptions import QueryError


class TestKeywordQueryBuilder:
    """Tests for KeywordQueryBuilder."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.builder = KeywordQueryBuilder()

    def test_build_query_basic(self) -> None:
        """Test basic query building."""
        query = self.builder.build_query(["malware", "virus"])

        assert query.query == "malware virus"
        assert "malware" in query.keywords
        assert "virus" in query.keywords

    def test_build_query_empty_keywords(self) -> None:
        """Test building query with empty keywords."""
        with pytest.raises(QueryError, match="cannot be empty"):
            self.builder.build_query([])

    def test_build_query_whitespace_keywords(self) -> None:
        """Test building query with whitespace-only keywords."""
        with pytest.raises(QueryError, match="empty"):
            self.builder.build_query(["  ", "\t", "\n"])

    def test_build_query_with_template(self) -> None:
        """Test building query with template."""
        query = self.builder.build_query(
            ["malware"],
            template="{keywords} domain"
        )
        assert query.query == "malware domain"

    def test_build_query_csv_template(self) -> None:
        """Test building query with CSV template."""
        query = self.builder.build_query(
            ["a", "b", "c"],
            template="{keywords_csv}"
        )
        assert query.query == "a,b,c"

    def test_build_query_quoted_template(self) -> None:
        """Test building query with quoted template."""
        query = self.builder.build_query(
            ["malware", "virus"],
            template='{keywords_quoted}'
        )
        assert '"malware"' in query.query
        assert '"virus"' in query.query

    def test_build_batch_queries(self) -> None:
        """Test building batch queries."""
        batches = self.builder.build_batch_queries(
            ["a", "b", "c", "d", "e"],
            batch_size=2
        )

        assert len(batches) == 3  # [a,b], [c,d], [e]
        assert len(batches[0]) == 1  # One query per batch item
        assert batches[0][0].query == "a b"
        assert batches[1][0].query == "c d"
        assert batches[2][0].query == "e"

    def test_build_batch_queries_invalid_size(self) -> None:
        """Test building batch queries with invalid size."""
        with pytest.raises(QueryError, match="at least 1"):
            self.builder.build_batch_queries(["a", "b"], batch_size=0)

    def test_custom_defaults(self) -> None:
        """Test custom default values."""
        builder = KeywordQueryBuilder(
            default_language="es",
            default_region="ES",
            default_safe_search=False,
        )
        query = builder.build_query(["test"])

        assert query.language == "es"
        assert query.region == "ES"
        assert query.safe_search is False


class TestPhraseQueryBuilder:
    """Tests for PhraseQueryBuilder."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.builder = PhraseQueryBuilder()

    def test_build_phrase_query(self) -> None:
        """Test building phrase query."""
        query = self.builder.build_query(["malware", "test"])

        assert query.query == '"malware test"'

    def test_build_batch_phrase_queries(self) -> None:
        """Test building batch phrase queries."""
        batches = self.builder.build_batch_queries(
            ["a", "b", "c"],
            batch_size=2
        )

        assert len(batches) == 2
        assert batches[0][0].query == '"a b"'
        assert batches[1][0].query == '"c"'


class TestDomainQueryBuilder:
    """Tests for DomainQueryBuilder."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.builder = DomainQueryBuilder(domain_suffix=".com")

    def test_build_domain_query(self) -> None:
        """Test building domain query."""
        query = self.builder.build_query(["example", "test"])

        assert "example.com" in query.query
        assert "test" in query.query

    def test_build_domain_query_no_suffix(self) -> None:
        """Test building domain query without suffix."""
        builder = DomainQueryBuilder()
        query = builder.build_query(["example"])

        assert query.query == "example"

    def test_build_batch_domain_queries(self) -> None:
        """Test building batch domain queries."""
        builder = DomainQueryBuilder(domain_suffix=".org")
        batches = builder.build_batch_queries(
            ["a", "b", "c"],
            batch_size=2
        )

        assert len(batches) == 2
        # First keyword in batch gets suffix
        assert "a.org" in batches[0][0].query
        assert "b" in batches[0][0].query
