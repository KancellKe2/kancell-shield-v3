"""Pagination implementation.

This module provides the ProviderPaginatorImpl class that
handles pagination abstraction.
"""

from dataclasses import dataclass
from typing import Any

from .interfaces import ProviderPaginator
from .models import (
    PaginationState,
    PaginationType,
    ProviderRequest,
    ProviderResponse,
)


@dataclass
class OffsetPaginator:
    """Handles offset-based pagination."""

    def __init__(self, page_size: int = 20) -> None:
        """Initialize offset paginator.

        Args:
            page_size: Number of results per page.
        """
        self._page_size = page_size

    def create_initial_state(self, page_size: int) -> PaginationState:
        """Create initial pagination state.

        Args:
            page_size: Page size to use.

        Returns:
            Initial pagination state.
        """
        return PaginationState(
            pagination_type=PaginationType.OFFSET,
            offset=0,
            page_size=page_size,
            has_more=True,
        )

    def get_next_state(
        self,
        current: PaginationState,
        response: ProviderResponse,
    ) -> PaginationState:
        """Calculate next pagination state.

        Args:
            current: Current pagination state.
            response: Response with results.

        Returns:
            Next pagination state.
        """
        results_count = len(response.results)
        new_offset = current.offset + results_count

        has_more = True
        if response.total_count is not None:
            has_more = new_offset < response.total_count
        elif results_count < current.page_size:
            has_more = False

        return PaginationState(
            pagination_type=PaginationType.OFFSET,
            offset=new_offset,
            page=current.page + 1,
            page_size=current.page_size,
            total_results=response.total_count,
            has_more=has_more,
        )

    def create_request(
        self,
        base_request: ProviderRequest,
        pagination: PaginationState,
    ) -> ProviderRequest:
        """Create paginated request.

        Args:
            base_request: Base request to paginate.
            pagination: Pagination state to use.

        Returns:
            Request with pagination parameters.
        """
        params = dict(base_request.custom_params)
        params["offset"] = str(pagination.offset)
        params["limit"] = str(pagination.page_size)

        return ProviderRequest(
            query=base_request.query,
            pagination=pagination,
            language=base_request.language,
            region=base_request.region,
            safe_search=base_request.safe_search,
            date_range=base_request.date_range,
            custom_params=params,
            request_id=base_request.request_id,
            timestamp=base_request.timestamp,
        )


@dataclass
class CursorPaginator:
    """Handles cursor-based pagination."""

    def __init__(self, page_size: int = 20) -> None:
        """Initialize cursor paginator.

        Args:
            page_size: Number of results per page.
        """
        self._page_size = page_size

    def create_initial_state(self, page_size: int) -> PaginationState:
        """Create initial pagination state.

        Args:
            page_size: Page size to use.

        Returns:
            Initial pagination state.
        """
        return PaginationState(
            pagination_type=PaginationType.CURSOR,
            page_size=page_size,
            has_more=True,
        )

    def get_next_state(
        self,
        current: PaginationState,
        response: ProviderResponse,
    ) -> PaginationState:
        """Calculate next pagination state.

        Args:
            current: Current pagination state.
            response: Response with results.

        Returns:
            Next pagination state.
        """
        next_cursor = None
        if response.pagination and response.pagination.next_page_token:
            next_cursor = response.pagination.next_page_token
        elif response.metadata.get("next_cursor"):
            next_cursor = response.metadata["next_cursor"]

        has_more = next_cursor is not None
        if len(response.results) < current.page_size:
            has_more = False

        return PaginationState(
            pagination_type=PaginationType.CURSOR,
            cursor=current.cursor,
            next_page_token=next_cursor,
            page=current.page + 1,
            page_size=current.page_size,
            total_results=response.total_count,
            has_more=has_more,
        )

    def create_request(
        self,
        base_request: ProviderRequest,
        pagination: PaginationState,
    ) -> ProviderRequest:
        """Create paginated request.

        Args:
            base_request: Base request to paginate.
            pagination: Pagination state to use.

        Returns:
            Request with pagination parameters.
        """
        params = dict(base_request.custom_params)

        if pagination.cursor:
            params["cursor"] = pagination.cursor
        if pagination.next_page_token:
            params["cursor"] = pagination.next_page_token

        params["limit"] = str(pagination.page_size)

        return ProviderRequest(
            query=base_request.query,
            pagination=pagination,
            language=base_request.language,
            region=base_request.region,
            safe_search=base_request.safe_search,
            date_range=base_request.date_range,
            custom_params=params,
            request_id=base_request.request_id,
            timestamp=base_request.timestamp,
        )


@dataclass
class PagePaginator:
    """Handles page-based pagination."""

    def __init__(self, page_size: int = 20) -> None:
        """Initialize page paginator.

        Args:
            page_size: Number of results per page.
        """
        self._page_size = page_size

    def create_initial_state(self, page_size: int) -> PaginationState:
        """Create initial pagination state.

        Args:
            page_size: Page size to use.

        Returns:
            Initial pagination state.
        """
        return PaginationState(
            pagination_type=PaginationType.PAGE,
            page=1,
            page_size=page_size,
            has_more=True,
        )

    def get_next_state(
        self,
        current: PaginationState,
        response: ProviderResponse,
    ) -> PaginationState:
        """Calculate next pagination state.

        Args:
            current: Current pagination state.
            response: Response with results.

        Returns:
            Next pagination state.
        """
        has_more = True
        if response.total_count is not None:
            total_pages = (response.total_count + current.page_size - 1) // current.page_size
            has_more = current.page < total_pages
        elif len(response.results) < current.page_size:
            has_more = False

        return PaginationState(
            pagination_type=PaginationType.PAGE,
            page=current.page + 1,
            page_size=current.page_size,
            total_results=response.total_count,
            has_more=has_more,
        )

    def create_request(
        self,
        base_request: ProviderRequest,
        pagination: PaginationState,
    ) -> ProviderRequest:
        """Create paginated request.

        Args:
            base_request: Base request to paginate.
            pagination: Pagination state to use.

        Returns:
            Request with pagination parameters.
        """
        params = dict(base_request.custom_params)
        params["page"] = str(pagination.page)
        params["page_size"] = str(pagination.page_size)

        return ProviderRequest(
            query=base_request.query,
            pagination=pagination,
            language=base_request.language,
            region=base_request.region,
            safe_search=base_request.safe_search,
            date_range=base_request.date_range,
            custom_params=params,
            request_id=base_request.request_id,
            timestamp=base_request.timestamp,
        )


class ProviderPaginatorImpl(ProviderPaginator):
    """Implementation of ProviderPaginator.

    This paginator handles different pagination types
    and provides a unified interface.
    """

    def __init__(
        self,
        default_page_size: int = 20,
        max_page_size: int = 100,
    ) -> None:
        """Initialize the paginator.

        Args:
            default_page_size: Default page size.
            max_page_size: Maximum allowed page size.
        """
        self._default_page_size = default_page_size
        self._max_page_size = max_page_size
        self._offset_paginator = OffsetPaginator(default_page_size)
        self._cursor_paginator = CursorPaginator(default_page_size)
        self._page_paginator = PagePaginator(default_page_size)

    def create_initial_state(
        self,
        pagination_type: PaginationType,
        page_size: int,
    ) -> PaginationState:
        """Create initial pagination state.

        Args:
            pagination_type: Type of pagination.
            page_size: Page size to use.

        Returns:
            Initial pagination state.
        """
        size = min(page_size, self._max_page_size)
        size = max(size, 1)

        if pagination_type == PaginationType.OFFSET:
            return self._offset_paginator.create_initial_state(size)
        elif pagination_type == PaginationType.CURSOR:
            return self._cursor_paginator.create_initial_state(size)
        elif pagination_type == PaginationType.PAGE:
            return self._page_paginator.create_initial_state(size)

        return PaginationState(
            pagination_type=pagination_type,
            page_size=size,
            has_more=True,
        )

    def get_next_state(
        self,
        current: PaginationState,
        response: ProviderResponse,
    ) -> PaginationState:
        """Calculate next pagination state.

        Args:
            current: Current pagination state.
            response: Response with results.

        Returns:
            Next pagination state.
        """
        if current.pagination_type == PaginationType.OFFSET:
            return self._offset_paginator.get_next_state(current, response)
        elif current.pagination_type == PaginationType.CURSOR:
            return self._cursor_paginator.get_next_state(current, response)
        elif current.pagination_type == PaginationType.PAGE:
            return self._page_paginator.get_next_state(current, response)

        return current

    def has_more(
        self,
        state: PaginationState,
        response: ProviderResponse,
    ) -> bool:
        """Check if more pages are available.

        Args:
            state: Current pagination state.
            response: Response with results.

        Returns:
            True if more pages available.
        """
        if not state.has_more:
            return False

        if response.total_count is not None:
            return self._has_more_by_total(state, response)

        return len(response.results) >= state.page_size

    def _has_more_by_total(
        self,
        state: PaginationState,
        response: ProviderResponse,
    ) -> bool:
        """Check if more pages by total count.

        Args:
            state: Current state.
            response: Response.

        Returns:
            True if more pages based on total.
        """
        if state.pagination_type == PaginationType.OFFSET:
            return state.offset + len(response.results) < response.total_count
        elif state.pagination_type == PaginationType.PAGE:
            total_pages = (response.total_count + state.page_size - 1) // state.page_size
            return state.page < total_pages

        return state.has_more

    def create_request(
        self,
        base_request: ProviderRequest,
        pagination: PaginationState,
    ) -> ProviderRequest:
        """Create paginated request.

        Args:
            base_request: Base request to paginate.
            pagination: Pagination state to use.

        Returns:
            Request with pagination parameters.
        """
        if pagination.pagination_type == PaginationType.OFFSET:
            return self._offset_paginator.create_request(base_request, pagination)
        elif pagination.pagination_type == PaginationType.CURSOR:
            return self._cursor_paginator.create_request(base_request, pagination)
        elif pagination.pagination_type == PaginationType.PAGE:
            return self._page_paginator.create_request(base_request, pagination)

        return base_request

    def get_paginator_for_type(
        self,
        pagination_type: PaginationType,
    ) -> OffsetPaginator | CursorPaginator | PagePaginator:
        """Get paginator for a specific type.

        Args:
            pagination_type: Type of pagination.

        Returns:
            Appropriate paginator instance.
        """
        if pagination_type == PaginationType.OFFSET:
            return self._offset_paginator
        elif pagination_type == PaginationType.CURSOR:
            return self._cursor_paginator
        elif pagination_type == PaginationType.PAGE:
            return self._page_paginator

        return self._offset_paginator


class BatchPaginator:
    """Handles batch pagination across multiple queries."""

    def __init__(
        self,
        paginator: ProviderPaginator,
        batch_size: int = 5,
    ) -> None:
        """Initialize batch paginator.

        Args:
            paginator: Base paginator to use.
            batch_size: Number of concurrent pages to fetch.
        """
        self._paginator = paginator
        self._batch_size = batch_size

    def paginate_all(
        self,
        base_request: ProviderRequest,
        initial_state: PaginationState,
        fetch_page: callable,
    ) -> list[ProviderResponse]:
        """Paginate through all results.

        Args:
            base_request: Base request to paginate.
            initial_state: Initial pagination state.
            fetch_page: Function to fetch a page.

        Returns:
            List of all responses.
        """
        all_responses: list[ProviderResponse] = []
        current_state = initial_state

        while True:
            response = fetch_page(current_state)
            all_responses.append(response)

            if not self._paginator.has_more(current_state, response):
                break

            current_state = self._paginator.get_next_state(current_state, response)

        return all_responses
