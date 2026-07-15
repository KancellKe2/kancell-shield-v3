"""Search engine implementation for orchestrating search operations."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Sequence

from .interfaces import (
    DeduplicationStrategy,
    ProviderRegistry,
    QueryBuilder,
    RateLimiter,
    ResultNormalizer,
    RetryStrategy,
    SearchEngine as ISearchEngine,
    SearchProvider,
)
from .models import (
    ProviderHealth,
    ProviderState,
    SearchConfig,
    SearchQuery,
    SearchResult,
    SearchResultSet,
)


class UrlDeduplicationStrategy(DeduplicationStrategy):
    """Deduplication strategy based on URL equality."""

    def is_duplicate(
        self,
        result: SearchResult,
        existing: Sequence[SearchResult],
    ) -> bool:
        """Check if result is duplicate by URL.

        Args:
            result: Result to check.
            existing: Existing results.

        Returns:
            True if duplicate.
        """
        for existing_result in existing:
            if result.url == existing_result.url:
                return True
        return False

    def deduplicate(
        self,
        results: Sequence[SearchResult],
    ) -> tuple[Sequence[SearchResult], int]:
        """Deduplicate results by URL.

        Args:
            results: Results to deduplicate.

        Returns:
            Tuple of (unique_results, duplicate_count).
        """
        unique: list[SearchResult] = []
        seen_urls: set[str] = set()
        duplicate_count = 0

        for result in results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique.append(result)
            else:
                duplicate_count += 1

        return tuple(unique), duplicate_count


class SearchEngineImpl(ISearchEngine):
    """Main implementation of search orchestration.

    This engine orchestrates search operations across multiple providers
    including provider selection, retry handling, rate limiting,
    result aggregation, and deduplication.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        query_builder: QueryBuilder | None = None,
        normalizer: ResultNormalizer | None = None,
        rate_limiter: RateLimiter | None = None,
        retry_strategy: RetryStrategy | None = None,
        deduplication_strategy: DeduplicationStrategy | None = None,
    ) -> None:
        """Initialize the search engine.

        Args:
            registry: Provider registry.
            query_builder: Query builder.
            normalizer: Result normalizer.
            rate_limiter: Rate limiter.
            retry_strategy: Retry strategy.
            deduplication_strategy: Deduplication strategy.
        """
        self._registry = registry or self._create_default_registry()
        self._query_builder = query_builder or self._create_default_query_builder()
        self._normalizer = normalizer or self._create_default_normalizer()
        self._rate_limiter = rate_limiter
        self._retry_strategy = retry_strategy
        self._deduplication_strategy = deduplication_strategy or UrlDeduplicationStrategy()

    async def search(
        self,
        keywords: Sequence[str],
        config: SearchConfig,
    ) -> SearchResultSet:
        """Execute search for keywords across providers.

        Args:
            keywords: Keywords to search for.
            config: Search configuration.

        Returns:
            SearchResultSet with aggregated results.
        """
        start_time = time.monotonic()
        errors: list[str] = []
        providers_used: list[str] = []
        all_results: list[SearchResult] = []

        # Build query
        query = self._query_builder.build_query(keywords)

        # Get healthy providers
        providers = self._registry.get_healthy_providers()

        if not providers:
            # Fall back to all enabled providers
            providers = list(self._registry.get_providers(enabled_only=True))

        if not providers:
            return SearchResultSet(
                results=(),
                total_count=0,
                unique_count=0,
                query=query.query,
                execution_time_ms=(time.monotonic() - start_time) * 1000,
                providers_used=(),
                errors=("No providers available",),
            )

        # Execute search across providers
        for provider in providers:
            try:
                # Check rate limit if configured
                can_proceed = True
                if self._rate_limiter:
                    can_proceed = await self._rate_limiter.acquire(provider.name)
                    if not can_proceed:
                        errors.append(f"Rate limited for provider '{provider.name}'")
                        continue

                results = await self._execute_search(
                    provider, query, config.timeout
                )
                normalized = self._normalizer.normalize(results, provider.name)
                all_results.extend(normalized)
                providers_used.append(provider.name)

                if self._rate_limiter and can_proceed:
                    self._rate_limiter.release(provider.name)

            except Exception as e:
                errors.append(f"Provider '{provider.name}' error: {str(e)}")
                # Update provider health
                provider.update_health(ProviderState.UNHEALTHY)

        # Deduplicate results
        if config.enable_deduplication:
            unique_results, dup_count = self._deduplication_strategy.deduplicate(
                all_results
            )
            if dup_count > 0:
                errors.append(f"Removed {dup_count} duplicate results")
        else:
            unique_results = all_results

        # Filter by confidence
        filtered_results = [
            r for r in unique_results
            if r.confidence >= config.confidence_threshold
        ]

        # Sort by confidence
        sorted_results = sorted(
            filtered_results,
            key=lambda r: (r.confidence, -r.position),
            reverse=True,
        )

        # Build result set
        provider_counts: dict[str, int] = {}
        for result in sorted_results:
            provider_counts[result.provider] = provider_counts.get(result.provider, 0) + 1

        return SearchResultSet(
            results=tuple(sorted_results),
            total_count=len(sorted_results),
            unique_count=len(set(r.url for r in sorted_results)),
            provider_counts=provider_counts,
            query=query.query,
            execution_time_ms=(time.monotonic() - start_time) * 1000,
            providers_used=tuple(providers_used),
            errors=tuple(errors),
        )

    async def search_batch(
        self,
        keywords: Sequence[str],
        config: SearchConfig,
    ) -> Sequence[SearchResultSet]:
        """Execute batch search for multiple keywords.

        Args:
            keywords: Keywords to search for.
            config: Search configuration.

        Returns:
            Sequence of SearchResultSet, one per keyword batch.
        """
        # Build batches
        batches = self._query_builder.build_batch_queries(
            keywords, config.batch_size
        )

        results: list[SearchResultSet] = []

        for batch in batches:
            for query in batch:
                result_set = await self.search([query.query], config)
                results.append(result_set)

        return results

    def get_provider_registry(self) -> ProviderRegistry:
        """Get the provider registry.

        Returns:
            ProviderRegistry instance.
        """
        return self._registry

    def get_health_status(self) -> dict[str, ProviderHealth]:
        """Get health status of all providers.

        Returns:
            Map of provider name to health.
        """
        providers = self._registry.get_providers(enabled_only=False)
        return {p.name: p.get_health() for p in providers}

    async def _execute_search(
        self,
        provider: SearchProvider,
        query: SearchQuery,
        timeout: float,
    ) -> Sequence[SearchResult]:
        """Execute search with a single provider.

        Args:
            provider: Provider to use.
            query: Search query.
            timeout: Timeout in seconds.

        Returns:
            Search results from provider.
        """
        attempt = 0
        last_error: Exception | None = None

        while True:
            try:
                return await asyncio.wait_for(
                    provider.search(query, timeout),
                    timeout=timeout,
                )

            except asyncio.TimeoutError as e:
                last_error = e
                if self._retry_strategy:
                    if not self._retry_strategy.should_retry(attempt, e):
                        raise
                    attempt += 1
                    delay = self._retry_strategy.get_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

            except Exception as e:
                last_error = e
                if self._retry_strategy:
                    if not self._retry_strategy.should_retry(attempt, e):
                        raise
                    attempt += 1
                    delay = self._retry_strategy.get_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

    def _create_default_registry(self) -> ProviderRegistry:
        """Create default provider registry.

        Returns:
            New registry instance.
        """
        from .registry import ProviderRegistryImpl
        return ProviderRegistryImpl()

    def _create_default_query_builder(self) -> QueryBuilder:
        """Create default query builder.

        Returns:
            New query builder instance.
        """
        from .query_builder import KeywordQueryBuilder
        return KeywordQueryBuilder()

    def _create_default_normalizer(self) -> ResultNormalizer:
        """Create default result normalizer.

        Returns:
            New normalizer instance.
        """
        from .normalizer import ResultNormalizerImpl
        return ResultNormalizerImpl()
