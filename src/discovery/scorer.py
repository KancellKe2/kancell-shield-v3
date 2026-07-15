"""Candidate scoring for discovery."""

import hashlib
from typing import Sequence

from .interfaces import CandidateScorer
from .models import (
    CandidateStatus,
    DiscoveryCandidate,
    Domain,
)


class DomainScorer(CandidateScorer):
    """Implementation of CandidateScorer.

    Computes deterministic confidence scores for candidates
    based on domain characteristics. No randomness used.
    """

    # Default source weights
    DEFAULT_SOURCE_WEIGHTS: dict[str, float] = {
        "ct": 0.9,
        "certificate_transparency": 0.9,
        "passive_dns": 0.8,
        "dns_cache": 0.7,
        "whois": 0.6,
        "dns_enum": 0.5,
        "subdomain_enum": 0.5,
    }

    # TLD risk weights (higher = more suspicious)
    TLD_RISK_WEIGHTS: dict[str, float] = {
        # High risk TLDs
        "xyz": 0.15,
        "top": 0.15,
        "club": 0.15,
        "online": 0.15,
        "site": 0.15,
        "buzz": 0.15,
        "tk": 0.15,
        "ml": 0.15,
        "ga": 0.15,
        "cf": 0.15,
        "gq": 0.15,
        # Low risk TLDs
        "com": 0.05,
        "org": 0.05,
        "net": 0.05,
        "gov": 0.05,
        "edu": 0.05,
        # Medium risk (default)
    }

    def __init__(
        self,
        source_weights: dict[str, float] | None = None,
        enable_tld_scoring: bool = True,
        enable_subdomain_scoring: bool = True,
    ) -> None:
        """Initialize scorer.

        Args:
            source_weights: Custom source weights.
            enable_tld_scoring: Enable TLD-based scoring.
            enable_subdomain_scoring: Enable subdomain-based scoring.
        """
        self._source_weights = source_weights or self.DEFAULT_SOURCE_WEIGHTS.copy()
        self._enable_tld_scoring = enable_tld_scoring
        self._enable_subdomain_scoring = enable_subdomain_scoring

    def score(self, candidate: DiscoveryCandidate) -> float:
        """Score a single candidate.

        Args:
            candidate: Candidate to score.

        Returns:
            Relevance score (0.0 to 1.0).
        """
        base_score = 0.5

        # Apply source weight
        source_weight = self._get_source_weight(candidate.source)
        score = base_score * source_weight

        # Apply TLD scoring
        if self._enable_tld_scoring:
            tld_factor = self._calculate_tld_factor(candidate.domain)
            score = score * (1.0 + tld_factor)

        # Apply subdomain scoring
        if self._enable_subdomain_scoring:
            subdomain_factor = self._calculate_subdomain_factor(candidate.domain)
            score = score * (1.0 + subdomain_factor)

        # Normalize to 0.0-1.0 range
        return max(0.0, min(1.0, score))

    def score_batch(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Score multiple candidates.

        Args:
            candidates: Candidates to score.

        Returns:
            Candidates with updated scores.
        """
        scored = []
        for candidate in candidates:
            new_score = self.score(candidate)
            confidence = self.calculate_confidence(candidate)
            updated = DiscoveryCandidate(
                domain=candidate.domain,
                source=candidate.source,
                discovered_at=candidate.discovered_at,
                status=CandidateStatus.SCORED,
                validation_result=candidate.validation_result,
                score=new_score,
                confidence=confidence,
                metadata=candidate.metadata,
                parent_domain=candidate.parent_domain,
            )
            scored.append(updated)
        return tuple(scored)

    def calculate_confidence(self, candidate: DiscoveryCandidate) -> float:
        """Calculate confidence in the score.

        Args:
            candidate: Candidate with score.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        if candidate.score is None:
            return 0.0

        # Confidence is higher if:
        # 1. Source is known/trusted
        # 2. Domain format is clean
        # 3. Has parent domain (suggests relation)

        confidence = 0.5

        # Boost for known source
        if candidate.source in self._source_weights:
            confidence += 0.2

        # Boost for having parent domain
        if candidate.parent_domain:
            confidence += 0.15

        # Boost for valid validation
        if candidate.validation_result is None:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def rank_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> tuple[DiscoveryCandidate, ...]:
        """Rank candidates by score.

        Args:
            candidates: Candidates to rank.

        Returns:
            Candidates sorted by score descending.
        """
        # Score any unscored candidates
        scored = []
        for candidate in candidates:
            if candidate.score is None:
                new_score = self.score(candidate)
                new_confidence = self.calculate_confidence(candidate)
                candidate = DiscoveryCandidate(
                    domain=candidate.domain,
                    source=candidate.source,
                    discovered_at=candidate.discovered_at,
                    status=candidate.status,
                    validation_result=candidate.validation_result,
                    score=new_score,
                    confidence=new_confidence,
                    metadata=candidate.metadata,
                    parent_domain=candidate.parent_domain,
                )
            scored.append(candidate)

        # Sort by score descending, then by confidence descending
        return tuple(
            sorted(
                scored,
                key=lambda c: (c.score or 0.0, c.confidence or 0.0),
                reverse=True,
            )
        )

    def set_source_weight(self, source: str, weight: float) -> None:
        """Set weight for a source.

        Args:
            source: Source name.
            weight: Weight value (0.0 to 1.0).
        """
        if weight < 0.0 or weight > 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        self._source_weights[source] = weight

    def get_source_weight(self, source: str) -> float:
        """Get weight for a source.

        Args:
            source: Source name.

        Returns:
            Weight value.
        """
        return self._source_weights.get(source, 0.5)

    def _get_source_weight(self, source: str) -> float:
        """Get weight for a source.

        Args:
            source: Source name.

        Returns:
            Weight value.
        """
        return self._source_weights.get(source.lower(), 0.5)

    def _calculate_tld_factor(self, domain: Domain) -> float:
        """Calculate TLD-based scoring factor.

        Args:
            domain: Domain to analyze.

        Returns:
            Factor to apply (can be negative).
        """
        tld = domain.tld
        if not tld:
            # Extract TLD from domain name
            parts = domain.name.lower().split(".")
            if parts:
                tld = parts[-1]

        if not tld:
            return 0.0

        return self.TLD_RISK_WEIGHTS.get(tld.lower(), 0.0)

    def _calculate_subdomain_factor(self, domain: Domain) -> float:
        """Calculate subdomain-based scoring factor.

        Args:
            domain: Domain to analyze.

        Returns:
            Factor to apply.
        """
        # Having subdomains can be slightly suspicious
        if domain.subdomain:
            # More subdomains = more suspicious
            depth = len(domain.subdomain.split("."))
            return 0.05 * depth
        return 0.0


class DeterministicScorer(DomainScorer):
    """Scorer with deterministic output based on domain hash.

    Uses a hash of the domain to ensure consistent scores
    across runs without randomness.
    """

    def score(self, candidate: DiscoveryCandidate) -> float:
        """Score a candidate deterministically.

        Args:
            candidate: Candidate to score.

        Returns:
            Deterministic score (0.0 to 1.0).
        """
        # Get base score from parent class
        base_score = super().score(candidate)

        # Apply deterministic modifier based on domain hash
        domain_hash = self._hash_domain(candidate.domain.name)

        # Use hash to calculate a small deterministic offset
        # This ensures the same domain always gets the same score
        hash_factor = (domain_hash % 100) / 1000.0  # Range: 0.0 to 0.099

        return max(0.0, min(1.0, base_score + hash_factor))

    def _hash_domain(self, domain: str) -> int:
        """Generate a deterministic hash for a domain.

        Args:
            domain: Domain string.

        Returns:
            Hash value.
        """
        # Use MD5 for consistent hashing
        hash_bytes = hashlib.md5(domain.lower().encode()).digest()
        # Use first 4 bytes as integer
        return int.from_bytes(hash_bytes[:4], byteorder="big")
