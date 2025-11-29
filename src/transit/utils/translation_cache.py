"""Translation cache for repeated phrases and sentences."""

import asyncio
import hashlib
import json
import logging
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TranslationCache:
    """
    Cache for translated text to avoid redundant API calls.

    Stores translations with language pair as key, supports
    persistence to disk, and automatic expiration.
    """

    def __init__(
        self,
        cache_file: Optional[str] = None,
        max_entries: int = 10000,
        expiry_days: int = 30,
        enable_persistence: bool = True
    ):
        """
        Initialize translation cache.

        Args:
            cache_file: Path to cache file (default: ~/.transit/cache.json)
            max_entries: Maximum number of cached translations
            expiry_days: Days until cache entries expire
            enable_persistence: Enable saving cache to disk
        """
        self.max_entries = max_entries
        self.expiry_days = expiry_days
        self.enable_persistence = enable_persistence

        # Determine cache file path
        if cache_file:
            self.cache_file = Path(cache_file)
        else:
            cache_dir = Path.home() / '.transit'
            cache_dir.mkdir(exist_ok=True)
            self.cache_file = cache_dir / 'translation_cache.json'

        # Cache structure: {cache_key: {translation, timestamp, hits}}
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'evictions': 0
        }

        # Load existing cache
        if self.enable_persistence:
            self._load_cache()

        logger.info(
            f"Initialized translation cache: "
            f"file={self.cache_file}, "
            f"max_entries={max_entries}, "
            f"expiry_days={expiry_days}, "
            f"current_size={len(self.cache)}"
        )

    def _make_cache_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate cache key for text + language pair.

        Args:
            text: Source text
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context string

        Returns:
            Cache key (MD5 hash)
        """
        # Normalize text (strip, lowercase for matching)
        normalized_text = text.strip().lower()

        # Include context in key if provided
        key_parts = [normalized_text, source_lang, target_lang]
        if context:
            key_parts.append(context)

        key_string = '|'.join(key_parts)

        # Generate hash
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def get(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Get translation from cache.

        Args:
            text: Source text
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context

        Returns:
            Cached translation or None if not found/expired
        """
        key = self._make_cache_key(text, source_lang, target_lang, context)

        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        entry = self.cache[key]

        # Check expiry
        if self._is_expired(entry):
            logger.debug(f"Cache entry expired: {key[:8]}...")
            del self.cache[key]
            self.stats['misses'] += 1
            self.stats['evictions'] += 1
            return None

        # Update stats
        entry['hits'] = entry.get('hits', 0) + 1
        entry['last_access'] = datetime.now().isoformat()

        self.stats['hits'] += 1

        logger.debug(f"Cache hit: {key[:8]}... (hits: {entry['hits']})")

        return entry['translation']

    def set(
        self,
        text: str,
        translation: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ):
        """
        Store translation in cache.

        Args:
            text: Source text
            translation: Translated text
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context
        """
        key = self._make_cache_key(text, source_lang, target_lang, context)

        # Check if we need to evict
        if key not in self.cache and len(self.cache) >= self.max_entries:
            self._evict_least_used()

        # Store entry
        self.cache[key] = {
            'translation': translation,
            'source_text': text[:100],  # Store first 100 chars for debugging
            'source_lang': source_lang,
            'target_lang': target_lang,
            'context': context[:100] if context else None,
            'timestamp': datetime.now().isoformat(),
            'last_access': datetime.now().isoformat(),
            'hits': 0
        }

        self.stats['saves'] += 1

        logger.debug(f"Cached translation: {key[:8]}...")

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """
        Check if cache entry is expired.

        Args:
            entry: Cache entry dictionary

        Returns:
            True if expired
        """
        timestamp_str = entry.get('timestamp')
        if not timestamp_str:
            return True

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            return age > timedelta(days=self.expiry_days)
        except Exception as e:
            logger.warning(f"Error checking expiry: {e}")
            return True

    def _evict_least_used(self):
        """Evict least recently used cache entry."""
        if not self.cache:
            return

        # Find entry with lowest hits and oldest access
        least_used_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].get('hits', 0), self.cache[k].get('last_access', ''))
        )

        logger.debug(f"Evicting least used entry: {least_used_key[:8]}...")
        del self.cache[least_used_key]
        self.stats['evictions'] += 1

    def _load_cache(self):
        """Load cache from disk."""
        if not self.cache_file.exists():
            logger.debug("No cache file found, starting fresh")
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.cache = data.get('cache', {})

            # Remove expired entries
            expired_keys = [
                key for key, entry in self.cache.items()
                if self._is_expired(entry)
            ]

            for key in expired_keys:
                del self.cache[key]

            logger.info(f"Loaded cache: {len(self.cache)} entries ({len(expired_keys)} expired)")

        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache = {}

    def save(self):
        """Save cache to disk."""
        if not self.enable_persistence:
            return

        try:
            # Prepare data
            data = {
                'cache': self.cache,
                'stats': self.stats,
                'saved_at': datetime.now().isoformat()
            }

            # Write atomically (write to temp file, then rename)
            temp_file = self.cache_file.with_suffix('.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.cache_file)

            logger.info(f"Saved cache: {len(self.cache)} entries to {self.cache_file}")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'evictions': 0
        }

        if self.enable_persistence and self.cache_file.exists():
            self.cache_file.unlink()

        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with statistics
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.stats,
            'size': len(self.cache),
            'max_entries': self.max_entries,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'utilization': len(self.cache) / self.max_entries * 100 if self.max_entries > 0 else 0
        }

    def log_stats(self):
        """Log cache statistics."""
        stats = self.get_stats()
        logger.info(
            f"Cache stats: "
            f"size={stats['size']}/{stats['max_entries']}, "
            f"hits={stats['hits']}, "
            f"misses={stats['misses']}, "
            f"hit_rate={stats['hit_rate']:.1f}%, "
            f"evictions={stats['evictions']}"
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save cache."""
        self.save()
        return False


class CachedTranslator:
    """
    Wrapper that adds caching to any translator.

    Transparently caches translations to avoid redundant API calls.
    """

    def __init__(
        self,
        translator,
        cache: Optional[TranslationCache] = None,
        enable_cache: bool = True
    ):
        """
        Initialize cached translator.

        Args:
            translator: Underlying translator
            cache: Optional custom cache instance
            enable_cache: Enable caching (can be disabled for testing)
        """
        self.translator = translator
        self.enable_cache = enable_cache

        if enable_cache:
            self.cache = cache or TranslationCache()
        else:
            self.cache = None

        logger.info(f"Initialized cached translator (caching={'enabled' if enable_cache else 'disabled'})")

    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None
    ) -> str:
        """
        Translate text with caching.

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code
            preserve_formatting: Preserve formatting
            context: Optional context

        Returns:
            Translated text
        """
        # Check cache if enabled
        if self.enable_cache and self.cache:
            cached = self.cache.get(text, source_lang, target_lang, context)
            if cached is not None:
                return cached

        # Translate via underlying translator
        result = self.translator.translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang,
            preserve_formatting=preserve_formatting,
            context=context
        )

        # Store in cache
        if self.enable_cache and self.cache:
            self.cache.set(text, result, source_lang, target_lang, context)

        return result

    async def translate_text_async(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None,
    ) -> str:
        """
        Asynchronous translation with caching support.

        Mirrors translate_text but keeps the event loop hot when the underlying
        translator exposes an async interface.
        """
        if self.enable_cache and self.cache:
            cached = self.cache.get(text, source_lang, target_lang, context)
            if cached is not None:
                return cached

        if hasattr(self.translator, "translate_text_async"):
            result = await self.translator.translate_text_async(
                text,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                context=context,
            )
        else:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.translator.translate_text(
                    text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    context=context,
                ),
            )

        if self.enable_cache and self.cache:
            self.cache.set(text, result, source_lang, target_lang, context)

        return result

    def translate_batch(
        self,
        texts: list,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        batch_context: Optional[str] = None
    ) -> list:
        """
        Translate batch with caching.

        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            preserve_formatting: Preserve formatting
            batch_context: Optional context

        Returns:
            List of translated texts
        """
        if not self.enable_cache or not self.cache:
            # No caching, translate all
            return self.translator.translate_batch(
                texts,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                batch_context=batch_context
            )

        # Check cache for each text
        results = []
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            cached = self.cache.get(text, source_lang, target_lang, batch_context)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)  # Placeholder
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Translate uncached texts
        if uncached_texts:
            logger.debug(f"Cache miss for {len(uncached_texts)}/{len(texts)} texts, translating...")

            translated = self.translator.translate_batch(
                uncached_texts,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                batch_context=batch_context
            )

            # Fill in results and update cache
            for i, translation in zip(uncached_indices, translated):
                results[i] = translation
                self.cache.set(texts[i], translation, source_lang, target_lang, batch_context)

        return results

    async def translate_batch_async(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        batch_context: Optional[str] = None,
    ) -> List[str]:
        """
        Asynchronous batch translation with caching support.
        """
        if not texts:
            return []

        if not self.enable_cache or not self.cache:
            if hasattr(self.translator, "translate_batch_async"):
                return await self.translator.translate_batch_async(
                    texts,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    batch_context=batch_context,
                )
            if hasattr(self.translator, "translate_batch"):
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.translator.translate_batch(
                        texts,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        batch_context=batch_context,
                    ),
                )
            # Fallback: no batch interface, reuse async text path
            return [
                await self.translate_text_async(
                    text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    context=batch_context,
                )
                for text in texts
            ]

        results: List[Optional[str]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for index, text in enumerate(texts):
            cached = self.cache.get(text, source_lang, target_lang, batch_context)
            if cached is not None:
                results[index] = cached
            else:
                uncached_indices.append(index)
                uncached_texts.append(text)

        if uncached_texts:
            if hasattr(self.translator, "translate_batch_async"):
                translated = await self.translator.translate_batch_async(
                    uncached_texts,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    batch_context=batch_context,
                )
            elif hasattr(self.translator, "translate_batch"):
                loop = asyncio.get_running_loop()
                translated = await loop.run_in_executor(
                    None,
                    lambda: self.translator.translate_batch(
                        uncached_texts,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        batch_context=batch_context,
                    ),
                )
            else:
                translated = [
                    await self.translate_text_async(
                        text,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        context=batch_context,
                    )
                    for text in uncached_texts
                ]

            for idx, translation in zip(uncached_indices, translated):
                results[idx] = translation
                self.cache.set(texts[idx], translation, source_lang, target_lang, batch_context)

        # At this point all slots should be filled
        return [res if res is not None else "" for res in results]

    def save_cache(self):
        """Save cache to disk."""
        if self.cache:
            self.cache.save()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {}

    def log_cache_stats(self):
        """Log cache statistics."""
        if self.cache:
            self.cache.log_stats()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.cache:
            self.cache.save()
        return False

    # Delegate attribute access to underlying translator
    def __getattr__(self, name):
        """Forward unknown attributes to underlying translator."""
        return getattr(self.translator, name)
