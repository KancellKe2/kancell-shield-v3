"""Keyword generator implementation."""

from datetime import datetime, timezone
from typing import Sequence

from .deduplicator import CaseInsensitiveDeduplicator, KeywordDeduplicator
from .exceptions import GenerationError, ProviderError
from .interfaces import (
    CombinationStrategy,
    KeywordGenerator as IKeywordGenerator,
    KeywordProvider,
)
from .models import (
    DeduplicationMode,
    Keyword,
    KeywordCategory,
    KeywordSet,
    KeywordTemplate,
    LanguageCode,
    GenerationConfig,
)
from .normalizer import KeywordNormalizer, StrictNormalizer
from .template_engine import KeywordTemplateEngine


class DefaultKeywordProvider(KeywordProvider):
    """Default keyword provider with built-in keyword dictionary.

    Provides base keywords for each category and language combination.
    """

    DEFAULT_KEYWORDS: dict[KeywordCategory, dict[LanguageCode, list[str]]] = {
        KeywordCategory.MALWARE: {
            LanguageCode.EN: ["virus", "trojan", "ransomware", "malware", "worm"],
            LanguageCode.ES: ["virus", "troyano", "ransomware"],
            LanguageCode.DE: ["virus", "trojaner", "malware"],
            LanguageCode.FR: ["virus", "chevaux-troie", "maliciel"],
            LanguageCode.ZH: ["病毒", "木马"],
            LanguageCode.RU: ["вирус", "троян"],
        },
        KeywordCategory.PHISHING: {
            LanguageCode.EN: ["login", "verify", "account", "password", "secure"],
            LanguageCode.ES: ["iniciar-sesion", "verificar", "cuenta"],
            LanguageCode.DE: ["anmeldung", "verifizieren", "konto"],
            LanguageCode.FR: ["connexion", "verifier", "compte"],
            LanguageCode.ZH: ["登录", "验证", "账户"],
            LanguageCode.RU: ["вход", "проверка", "аккаунт"],
        },
        KeywordCategory.SPAM: {
            LanguageCode.EN: ["free", "winner", "claim", "prize", "lottery"],
            LanguageCode.ES: ["gratis", "ganador", "reclamar", "premio"],
            LanguageCode.DE: ["kostenlos", "gewinner", "beanspruchen"],
            LanguageCode.FR: ["gratuit", "gagnant", "proclamer"],
            LanguageCode.ZH: ["免费", "中奖", "领奖"],
            LanguageCode.RU: ["бесплатно", "победитель", "приз"],
        },
        KeywordCategory.DGA: {
            LanguageCode.EN: ["random", "generated", "dynamic", "algorithm"],
            LanguageCode.ES: ["aleatorio", "generado"],
            LanguageCode.DE: ["zufallig", "generiert"],
            LanguageCode.FR: ["aleatoire", "genere"],
            LanguageCode.ZH: ["随机", "生成"],
            LanguageCode.RU: ["случайный", "сгенерированный"],
        },
        KeywordCategory.TYPOSQUATTING: {
            LanguageCode.EN: ["g00gle", "1google", "googIe", "googel"],
            LanguageCode.ES: ["g00gle"],
            LanguageCode.DE: ["gooogle"],
            LanguageCode.FR: ["gooogle"],
            LanguageCode.ZH: ["谷歌"],
            LanguageCode.RU: ["гугл"],
        },
        KeywordCategory.CLOUD_HOSTING: {
            LanguageCode.EN: ["cloud", "server", "hosting", "vps", "aws"],
            LanguageCode.ES: ["nube", "servidor"],
            LanguageCode.DE: ["wolke", "server"],
            LanguageCode.FR: ["nuage", "serveur"],
            LanguageCode.ZH: ["云", "服务器"],
            LanguageCode.RU: ["облако", "сервер"],
        },
        KeywordCategory.DEFACEMENT: {
            LanguageCode.EN: ["hacked", "defaced", "owned", "pwned"],
            LanguageCode.ES: ["hackeado"],
            LanguageCode.DE: ["gehackt"],
            LanguageCode.FR: ["pirate"],
            LanguageCode.ZH: ["被黑"],
            LanguageCode.RU: ["взломан"],
        },
        KeywordCategory.CREDENTIAL_THEFT: {
            LanguageCode.EN: ["credential", "stealer", "keylogger", "sniffer"],
            LanguageCode.ES: ["credencial", "robo"],
            LanguageCode.DE: ["anmeldedaten"],
            LanguageCode.FR: ["identifiant"],
            LanguageCode.ZH: ["凭证", "窃取"],
            LanguageCode.RU: ["учетные данные"],
        },
    }

    def get_keywords(
        self,
        categories: Sequence[KeywordCategory] | None = None,
    ) -> Sequence[Keyword]:
        """Retrieve keywords for specified categories.

        Args:
            categories: Optional list of categories to filter by.
                       If None, returns all available keywords.

        Returns:
            Sequence of Keyword objects.

        Raises:
            ProviderError: If keyword retrieval fails.
        """
        try:
            keywords: list[Keyword] = []
            target_categories = categories if categories else list(KeywordCategory)

            for category in target_categories:
                if category in self.DEFAULT_KEYWORDS:
                    for language, words in self.DEFAULT_KEYWORDS[category].items():
                        for word in words:
                            keywords.append(
                                Keyword(
                                    text=word,
                                    category=category,
                                    language=language,
                                )
                            )

            return keywords

        except Exception as e:
            raise ProviderError(f"Failed to get keywords: {e}") from e


class KeywordGeneratorImpl(IKeywordGenerator):
    """Main implementation of keyword generation.

    Orchestrates the keyword generation process including:
    - Keyword provision
    - Template application
    - Combination generation
    - Deduplication
    - Normalization
    """

    def __init__(
        self,
        provider: KeywordProvider | None = None,
        deduplicator: KeywordDeduplicator | None = None,
        normalizer: KeywordNormalizer | None = None,
        template_engine: KeywordTemplateEngine | None = None,
    ) -> None:
        """Initialize the keyword generator.

        Args:
            provider: Keyword provider to use.
            deduplicator: Deduplicator to use.
            normalizer: Normalizer to use.
            template_engine: Template engine to use.
        """
        self._provider = provider or DefaultKeywordProvider()
        self._deduplicator = deduplicator or KeywordDeduplicator(
            mode=DeduplicationMode.CASE_INSENSITIVE
        )
        self._normalizer = normalizer or StrictNormalizer()
        self._template_engine = template_engine or KeywordTemplateEngine()

    def generate(
        self,
        config: GenerationConfig,
        templates: Sequence[KeywordTemplate],
    ) -> KeywordSet:
        """Generate keywords based on configuration and templates.

        Args:
            config: Generation configuration.
            templates: Templates to apply.

        Returns:
            Generated KeywordSet.

        Raises:
            GenerationError: If generation fails.
        """
        try:
            # Step 1: Get base keywords from provider
            base_keywords = self._provider.get_keywords(
                categories=list(config.enabled_categories)
            )

            # Step 2: Filter by configured languages
            filtered_keywords = [
                k for k in base_keywords if k.language in config.languages
            ]

            # Step 3: Apply templates
            generated_strings = self._template_engine.generate_combinations(
                templates=templates,
                base_keywords=filtered_keywords,
                max_combinations=config.max_combinations,
            )

            # Step 4: Convert strings back to Keywords
            generated_keywords: list[Keyword] = []
            for text in generated_strings:
                # Apply length constraints
                if len(text) < config.min_keyword_length:
                    continue
                if len(text) > config.max_keyword_length:
                    text = text[: config.max_keyword_length]

                # Create keyword with default category
                keyword = Keyword(
                    text=text,
                    category=KeywordCategory.MALWARE,
                    language=LanguageCode.EN,
                )

                # Step 5: Normalize if enabled
                if config.enable_normalization:
                    keyword = self._normalizer.normalize(keyword)

                generated_keywords.append(keyword)

            # Step 6: Deduplicate if enabled
            if config.enable_deduplication:
                unique_keywords, _ = self._deduplicator.deduplicate_batch(
                    generated_keywords
                )
            else:
                unique_keywords = generated_keywords

            # Step 7: Build result
            return self._build_keyword_set(unique_keywords, config)

        except Exception as e:
            raise GenerationError(f"Keyword generation failed: {e}") from e

    def get_provider(self) -> KeywordProvider:
        """Get the keyword provider used by this generator.

        Returns:
            The KeywordProvider instance.
        """
        return self._provider

    def _build_keyword_set(
        self,
        keywords: list[Keyword],
        config: GenerationConfig,
    ) -> KeywordSet:
        """Build a KeywordSet from generated keywords.

        Args:
            keywords: Generated keywords.
            config: Configuration used.

        Returns:
            KeywordSet with metadata.
        """
        category_counts: dict[KeywordCategory, int] = {}
        language_counts: dict[LanguageCode, int] = {}

        for keyword in keywords:
            category_counts[keyword.category] = (
                category_counts.get(keyword.category, 0) + 1
            )
            language_counts[keyword.language] = (
                language_counts.get(keyword.language, 0) + 1
            )

        return KeywordSet(
            keywords=tuple(keywords),
            total_count=len(keywords),
            unique_count=len(set(k.text for k in keywords)),
            category_counts=category_counts,
            language_counts=language_counts,
            generation_metadata={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "categories": ",".join(c.name for c in config.enabled_categories),
                "languages": ",".join(l.value for l in config.languages),
                "deduplication": str(config.enable_deduplication),
                "normalization": str(config.enable_normalization),
            },
        )


class BasicKeywordGenerator(IKeywordGenerator):
    """Simplified keyword generator for basic use cases."""

    def __init__(self) -> None:
        """Initialize the basic generator."""
        self._provider = DefaultKeywordProvider()
        self._template_engine = KeywordTemplateEngine()

    def generate(
        self,
        config: GenerationConfig,
        templates: Sequence[KeywordTemplate],
    ) -> KeywordSet:
        """Generate keywords with basic processing.

        Args:
            config: Generation configuration.
            templates: Templates to apply.

        Returns:
            Generated KeywordSet.
        """
        base_keywords = self._provider.get_keywords(
            categories=list(config.enabled_categories)
        )

        generated_strings = self._template_engine.generate_combinations(
            templates=templates,
            base_keywords=base_keywords,
            max_combinations=config.max_combinations,
        )

        keywords: list[Keyword] = []
        for text in generated_strings:
            keywords.append(
                Keyword(
                    text=text,
                    category=KeywordCategory.MALWARE,
                    language=LanguageCode.EN,
                )
            )

        return KeywordSet(
            keywords=tuple(keywords),
            total_count=len(keywords),
            unique_count=len(set(k.text for k in keywords)),
        )

    def get_provider(self) -> KeywordProvider:
        """Get the keyword provider.

        Returns:
            The KeywordProvider instance.
        """
        return self._provider
