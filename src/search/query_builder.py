"""Query builder implementation for constructing search queries."""

from typing import Sequence

from .exceptions import QueryError
from .interfaces import QueryBuilder
from .models import SearchQuery


class KeywordQueryBuilder(QueryBuilder):
    """Query builder that constructs queries from keywords.

    Supports various templates and configurations for building
    search queries from keyword lists.
    """

    DEFAULT_TEMPLATE = "{keywords}"

    def __init__(
        self,
        default_language: str = "en",
        default_region: str = "US",
        default_safe_search: bool = True,
    ) -> None:
        """Initialize the query builder.

        Args:
            default_language: Default language code.
            default_region: Default region code.
            default_safe_search: Default safe search setting.
        """
        self._default_language = default_language
        self._default_region = default_region
        self._default_safe_search = default_safe_search

    def build_query(
        self,
        keywords: Sequence[str],
        template: str | None = None,
    ) -> SearchQuery:
        """Build a search query from keywords.

        Args:
            keywords: Keywords to search for.
            template: Optional query template.

        Returns:
            SearchQuery ready for execution.

        Raises:
            QueryError: If keywords are empty or invalid.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        # Clean keywords
        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        if not cleaned_keywords:
            raise QueryError("All keywords are empty")

        # Build query text
        query_text = self._apply_template(cleaned_keywords, template)

        return SearchQuery(
            query=query_text,
            keywords=frozenset(cleaned_keywords),
            language=self._default_language,
            region=self._default_region,
            safe_search=self._default_safe_search,
        )

    def build_batch_queries(
        self,
        keywords: Sequence[str],
        batch_size: int,
        template: str | None = None,
    ) -> Sequence[Sequence[SearchQuery]]:
        """Build batch queries from keywords.

        Args:
            keywords: Keywords to search for.
            batch_size: Number of queries per batch.
            template: Optional query template.

        Returns:
            Batches of SearchQuery objects.

        Raises:
            QueryError: If keywords are empty or batch_size is invalid.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        if batch_size < 1:
            raise QueryError("batch_size must be at least 1")

        # Clean keywords
        cleaned_keywords = [k.strip() for k in keywords if k.strip()]

        # Create batches
        batches: list[list[SearchQuery]] = []
        for i in range(0, len(cleaned_keywords), batch_size):
            batch_keywords = cleaned_keywords[i:i + batch_size]
            query = self.build_query(batch_keywords, template)
            batches.append([query])

        return batches

    def _apply_template(
        self,
        keywords: Sequence[str],
        template: str | None,
    ) -> str:
        """Apply template to keywords.

        Args:
            keywords: Keywords to use.
            template: Template string or None.

        Returns:
            Formatted query string.
        """
        if template is None:
            template = self.DEFAULT_TEMPLATE

        # Replace placeholder with keywords
        if "{keywords}" in template:
            keyword_str = " ".join(keywords)
            return template.replace("{keywords}", keyword_str)

        # Support comma-separated
        if "{keywords_csv}" in template:
            keyword_str = ",".join(keywords)
            return template.replace("{keywords_csv}", keyword_str)

        # Support quoted keywords
        if "{keywords_quoted}" in template:
            quoted = [f'"{k}"' for k in keywords]
            return template.replace("{keywords_quoted}", " ".join(quoted))

        # Default: join with space
        return " ".join(keywords)


class PhraseQueryBuilder(QueryBuilder):
    """Query builder that builds phrase queries."""

    def __init__(
        self,
        default_language: str = "en",
        default_region: str = "US",
        default_safe_search: bool = True,
    ) -> None:
        """Initialize the phrase query builder.

        Args:
            default_language: Default language code.
            default_region: Default region code.
            default_safe_search: Default safe search setting.
        """
        self._default_language = default_language
        self._default_region = default_region
        self._default_safe_search = default_safe_search

    def build_query(
        self,
        keywords: Sequence[str],
        template: str | None = None,
    ) -> SearchQuery:
        """Build a phrase search query from keywords.

        Args:
            keywords: Keywords to search for.
            template: Optional query template.

        Returns:
            SearchQuery with phrase-formatted query.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        if not cleaned_keywords:
            raise QueryError("All keywords are empty")

        # Build phrase query
        phrase = " ".join(cleaned_keywords)
        query_text = f'"{phrase}"'

        return SearchQuery(
            query=query_text,
            keywords=frozenset(cleaned_keywords),
            language=self._default_language,
            region=self._default_region,
            safe_search=self._default_safe_search,
        )

    def build_batch_queries(
        self,
        keywords: Sequence[str],
        batch_size: int,
        template: str | None = None,
    ) -> Sequence[Sequence[SearchQuery]]:
        """Build batch phrase queries.

        Args:
            keywords: Keywords to search for.
            batch_size: Number of keywords per query.
            template: Optional query template (ignored).

        Returns:
            Batches of SearchQuery objects.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        if batch_size < 1:
            raise QueryError("batch_size must be at least 1")

        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        batches: list[list[SearchQuery]] = []

        for i in range(0, len(cleaned_keywords), batch_size):
            batch_keywords = cleaned_keywords[i:i + batch_size]
            query = self.build_query(batch_keywords)
            batches.append([query])

        return batches


class DomainQueryBuilder(QueryBuilder):
    """Query builder that builds domain-specific queries."""

    def __init__(
        self,
        domain_suffix: str = "",
        default_language: str = "en",
        default_region: str = "US",
        default_safe_search: bool = True,
    ) -> None:
        """Initialize the domain query builder.

        Args:
            domain_suffix: Suffix to add to keywords (e.g., ".com").
            default_language: Default language code.
            default_region: Default region code.
            default_safe_search: Default safe search setting.
        """
        self._default_language = default_language
        self._default_region = default_region
        self._default_safe_search = default_safe_search
        self._domain_suffix = domain_suffix

    def build_query(
        self,
        keywords: Sequence[str],
        template: str | None = None,
    ) -> SearchQuery:
        """Build a domain search query from keywords.

        Args:
            keywords: Keywords to search for.
            template: Optional query template.

        Returns:
            SearchQuery with domain-formatted query.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        if not cleaned_keywords:
            raise QueryError("All keywords are empty")

        # Add domain suffix to first keyword if specified
        if self._domain_suffix:
            query_keywords = list(cleaned_keywords)
            query_keywords[0] = f"{query_keywords[0]}{self._domain_suffix}"
        else:
            query_keywords = cleaned_keywords

        query_text = " ".join(query_keywords)

        return SearchQuery(
            query=query_text,
            keywords=frozenset(cleaned_keywords),
            language=self._default_language,
            region=self._default_region,
            safe_search=self._default_safe_search,
        )

    def build_batch_queries(
        self,
        keywords: Sequence[str],
        batch_size: int,
        template: str | None = None,
    ) -> Sequence[Sequence[SearchQuery]]:
        """Build batch domain queries.

        Args:
            keywords: Keywords to search for.
            batch_size: Number of keywords per query.
            template: Optional query template.

        Returns:
            Batches of SearchQuery objects.
        """
        if not keywords:
            raise QueryError("Keywords cannot be empty")

        if batch_size < 1:
            raise QueryError("batch_size must be at least 1")

        cleaned_keywords = [k.strip() for k in keywords if k.strip()]
        batches: list[list[SearchQuery]] = []

        for i in range(0, len(cleaned_keywords), batch_size):
            batch_keywords = cleaned_keywords[i:i + batch_size]
            query = self.build_query(batch_keywords, template)
            batches.append([query])

        return batches
