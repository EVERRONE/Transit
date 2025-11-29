"""Unit tests for performance optimization features."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock

from transit.translators.async_translator import AsyncTranslatorWrapper
from transit.utils.batch_optimizer import BatchOptimizer, SmartBatchTranslator
from transit.utils.memory_optimizer import (
    MemoryMonitor,
    MemoryEfficientCache,
    memory_optimized_processing
)
from transit.utils.translation_cache import TranslationCache, CachedTranslator


class TestAsyncTranslator:
    """Test async translation wrapper."""

    def test_init(self):
        """Test initialization."""
        mock_translator = Mock()
        async_wrapper = AsyncTranslatorWrapper(mock_translator, max_concurrent=5)

        assert async_wrapper.translator == mock_translator
        assert async_wrapper.max_concurrent == 5
        assert async_wrapper.stats['total_requests'] == 0

    def test_sync_translate(self):
        """Test synchronous translation."""
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "TRANSLATED"

        async_wrapper = AsyncTranslatorWrapper(mock_translator)

        result = async_wrapper.translate_text("test", target_lang="EN")

        assert result == "TRANSLATED"
        mock_translator.translate_text.assert_called_once()
        assert async_wrapper.stats['successful_requests'] == 1

    def test_sync_batch_translate(self):
        """Test synchronous batch translation."""
        mock_translator = Mock()
        mock_translator.translate_batch.return_value = ["TEST1", "TEST2", "TEST3"]

        async_wrapper = AsyncTranslatorWrapper(mock_translator, max_concurrent=2)

        texts = ["test1", "test2", "test3"]
        results = async_wrapper.translate_batch(texts, target_lang="EN")

        assert results == ["TEST1", "TEST2", "TEST3"]
        mock_translator.translate_batch.assert_called_once()
        assert async_wrapper.stats['successful_requests'] == 1

    def test_get_stats(self):
        """Test statistics retrieval."""
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "RESULT"

        async_wrapper = AsyncTranslatorWrapper(mock_translator)

        # Perform translations
        async_wrapper.translate_text("test1", target_lang="EN")
        async_wrapper.translate_text("test2", target_lang="EN")

        stats = async_wrapper.get_stats()

        assert stats['total_requests'] == 2
        assert stats['successful_requests'] == 2
        assert stats['success_rate'] == 100.0

    def test_context_manager(self):
        """Test context manager usage."""
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "OK"

        with AsyncTranslatorWrapper(mock_translator) as wrapper:
            assert wrapper is not None
            # Using the wrapper should lazily create the executor.
            wrapper.translate_text("ping", target_lang="EN")
            assert wrapper.executor is not None

        # Executor should be shut down
        assert wrapper.executor is not None and wrapper.executor._shutdown

    def test_attribute_delegation(self):
        """Test attribute delegation to underlying translator."""
        mock_translator = Mock()
        mock_translator.some_custom_attr = "value"

        async_wrapper = AsyncTranslatorWrapper(mock_translator)

        assert async_wrapper.some_custom_attr == "value"


class TestBatchOptimizer:
    """Test batch optimization."""

    def test_init(self):
        """Test initialization."""
        optimizer = BatchOptimizer(max_batch_size=10, max_chars_per_batch=1000)

        assert optimizer.max_batch_size == 10
        assert optimizer.max_chars_per_batch == 1000

    def test_optimize_small_batch(self):
        """Test optimization of small text list."""
        optimizer = BatchOptimizer(max_batch_size=5, max_chars_per_batch=100)

        texts = ["text1", "text2", "text3"]
        batches = optimizer.optimize_batches(texts)

        # Should fit in single batch
        assert len(batches) == 1
        assert batches[0] == [0, 1, 2]

    def test_optimize_by_size_limit(self):
        """Test batching limited by batch size."""
        optimizer = BatchOptimizer(max_batch_size=2, max_chars_per_batch=10000)

        texts = ["a", "b", "c", "d", "e"]
        batches = optimizer.optimize_batches(texts)

        # Should split into 3 batches: [0,1], [2,3], [4]
        assert len(batches) == 3
        assert batches[0] == [0, 1]
        assert batches[1] == [2, 3]
        assert batches[2] == [4]

    def test_optimize_by_char_limit(self):
        """Test batching limited by character count."""
        optimizer = BatchOptimizer(max_batch_size=100, max_chars_per_batch=10)

        texts = ["short", "text", "here"]  # 5+4+4=13 chars total
        batches = optimizer.optimize_batches(texts)

        # Should split due to character limit
        assert len(batches) >= 2

    def test_single_text_exceeds_limit(self):
        """Test handling of text exceeding character limit."""
        optimizer = BatchOptimizer(max_batch_size=10, max_chars_per_batch=5)

        texts = ["very_long_text_here"]  # 19 chars
        batches = optimizer.optimize_batches(texts)

        # Should create single-item batch despite exceeding limit
        assert len(batches) == 1
        assert batches[0] == [0]

    def test_context_grouping(self):
        """Test context-based grouping."""
        optimizer = BatchOptimizer(
            max_batch_size=10,
            max_chars_per_batch=1000,
            enable_context_grouping=True
        )

        texts = ["text1", "text2", "text3", "text4"]
        contexts = ["A", "B", "A", "B"]

        batches = optimizer.optimize_batches(texts, contexts)

        # Should group by context
        assert len(batches) >= 2

    def test_estimate_batch_count(self):
        """Test batch count estimation."""
        optimizer = BatchOptimizer(max_batch_size=5, max_chars_per_batch=100)

        texts = ["text"] * 12  # 12 texts
        estimate = optimizer.estimate_batch_count(texts)

        # Should estimate 3 batches (12/5 = 2.4 -> 3)
        assert estimate >= 2

    def test_get_batch_stats(self):
        """Test batch statistics."""
        optimizer = BatchOptimizer()

        texts = ["a", "bb", "ccc"]
        batches = optimizer.optimize_batches(texts)

        stats = optimizer.get_batch_stats(batches, texts)

        assert stats['total_batches'] == len(batches)
        assert stats['total_texts'] == 3


class TestSmartBatchTranslator:
    """Test smart batch translator."""

    def test_init(self):
        """Test initialization."""
        mock_translator = Mock()
        smart = SmartBatchTranslator(mock_translator, auto_batch_threshold=3)

        assert smart.translator == mock_translator
        assert smart.auto_batch_threshold == 3

    def test_single_text_translation(self):
        """Test single text translation."""
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "RESULT"

        smart = SmartBatchTranslator(mock_translator)

        result = smart.translate_text("test", target_lang="EN")

        assert result == "RESULT"
        mock_translator.translate_text.assert_called_once()

    def test_batch_below_threshold(self):
        """Test batch below auto-batch threshold."""
        mock_translator = Mock()
        mock_translator.translate_text.side_effect = lambda text, **kwargs: text.upper()

        smart = SmartBatchTranslator(mock_translator, auto_batch_threshold=5)

        texts = ["a", "b", "c"]  # Below threshold
        results = smart.translate_multiple(texts, target_lang="EN")

        assert results == ["A", "B", "C"]
        assert mock_translator.translate_text.call_count == 3

    def test_batch_above_threshold_with_native_batch(self):
        """Test batch above threshold with native batch support."""
        mock_translator = Mock()
        mock_translator.translate_batch.return_value = ["A", "B", "C", "D", "E"]

        smart = SmartBatchTranslator(mock_translator, auto_batch_threshold=3)

        texts = ["a", "b", "c", "d", "e"]  # Above threshold
        results = smart.translate_multiple(texts, target_lang="EN")

        assert results == ["A", "B", "C", "D", "E"]
        mock_translator.translate_batch.assert_called()

    def test_attribute_delegation(self):
        """Test attribute delegation."""
        mock_translator = Mock()
        mock_translator.custom_method = Mock(return_value="value")

        smart = SmartBatchTranslator(mock_translator)

        assert smart.custom_method() == "value"


class TestMemoryMonitor:
    """Test memory monitoring."""

    def test_init(self):
        """Test initialization."""
        monitor = MemoryMonitor(warning_threshold_mb=100, critical_threshold_mb=200)

        assert monitor.warning_threshold_mb == 100
        assert monitor.critical_threshold_mb == 200

    def test_get_memory_delta(self):
        """Test memory delta calculation."""
        monitor = MemoryMonitor()

        delta = monitor.get_memory_delta_mb()

        # Delta should be non-negative (or 0 if psutil unavailable)
        assert delta >= 0

    def test_check_memory_below_threshold(self):
        """Test memory check below threshold."""
        monitor = MemoryMonitor(warning_threshold_mb=10000, critical_threshold_mb=20000)

        warning = monitor.check_memory()

        # Should not trigger warning
        assert warning is None

    def test_get_stats(self):
        """Test getting memory stats."""
        monitor = MemoryMonitor()

        # Method should not raise
        monitor.log_stats()


class TestMemoryEfficientCache:
    """Test memory-efficient cache."""

    def test_init(self):
        """Test initialization."""
        cache = MemoryEfficientCache(max_size=100, max_memory_mb=10)

        assert cache.max_size == 100
        assert len(cache) == 0

    def test_get_set(self):
        """Test basic get/set operations."""
        cache = MemoryEfficientCache(max_size=10)

        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_get_nonexistent(self):
        """Test getting nonexistent key."""
        cache = MemoryEfficientCache(max_size=10)

        result = cache.get("nonexistent")

        assert result is None

    def test_eviction(self):
        """Test LRU eviction."""
        cache = MemoryEfficientCache(max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Adding key4 should evict key2 (least recently used)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_clear(self):
        """Test cache clearing."""
        cache = MemoryEfficientCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert len(cache) == 0
        assert cache.get("key1") is None

    def test_contains(self):
        """Test __contains__ operator."""
        cache = MemoryEfficientCache(max_size=10)

        cache.set("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache

    def test_get_stats(self):
        """Test statistics."""
        cache = MemoryEfficientCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats['size'] == 2
        assert stats['max_size'] == 10
        assert stats['utilization'] == 20.0


class TestTranslationCache:
    """Test translation cache."""

    def test_init(self):
        """Test initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), max_entries=100)

            assert cache.max_entries == 100
            assert len(cache.cache) == 0

    def test_get_set(self):
        """Test basic get/set operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)

            cache.set("test", "translated", "NL", "EN")
            result = cache.get("test", "NL", "EN")

            assert result == "translated"

    def test_cache_miss(self):
        """Test cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)

            result = cache.get("nonexistent", "NL", "EN")

            assert result is None
            assert cache.stats['misses'] == 1

    def test_persistence(self):
        """Test saving and loading cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"

            # Create and populate cache
            cache1 = TranslationCache(cache_file=str(cache_file))
            cache1.set("test", "translated", "NL", "EN")
            cache1.save()

            # Load cache in new instance
            cache2 = TranslationCache(cache_file=str(cache_file))

            assert cache2.get("test", "NL", "EN") == "translated"

    def test_context_in_key(self):
        """Test that context affects cache key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)

            cache.set("test", "translation1", "NL", "EN", context="context1")
            cache.set("test", "translation2", "NL", "EN", context="context2")

            result1 = cache.get("test", "NL", "EN", context="context1")
            result2 = cache.get("test", "NL", "EN", context="context2")

            assert result1 == "translation1"
            assert result2 == "translation2"

    def test_get_stats(self):
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)

            cache.set("test1", "translated1", "NL", "EN")
            cache.get("test1", "NL", "EN")  # Hit
            cache.get("test2", "NL", "EN")  # Miss

            stats = cache.get_stats()

            assert stats['hits'] == 1
            assert stats['misses'] == 1
            assert stats['hit_rate'] == 50.0

    def test_clear(self):
        """Test clearing cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file))

            cache.set("test", "translated", "NL", "EN")
            cache.clear()

            assert len(cache.cache) == 0
            assert cache.get("test", "NL", "EN") is None


class TestCachedTranslator:
    """Test cached translator wrapper."""

    def test_init(self):
        """Test initialization."""
        mock_translator = Mock()
        cached = CachedTranslator(mock_translator)

        assert cached.translator == mock_translator
        assert cached.enable_cache is True

    def test_cache_hit(self):
        """Test translation with cache hit."""
        mock_translator = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)
            cached = CachedTranslator(mock_translator, cache=cache)

            # First call - cache miss
            mock_translator.translate_text.return_value = "RESULT"
            result1 = cached.translate_text("test", target_lang="EN")

            assert result1 == "RESULT"
            assert mock_translator.translate_text.call_count == 1

            # Second call - cache hit
            result2 = cached.translate_text("test", target_lang="EN")

            assert result2 == "RESULT"
            assert mock_translator.translate_text.call_count == 1  # Not called again

    def test_batch_translation_with_cache(self):
        """Test batch translation with partial cache hits."""
        mock_translator = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)
            cached = CachedTranslator(mock_translator, cache=cache)

            # Pre-cache one translation
            cache.set("text1", "CACHED_RESULT", "NL", "EN")

            # Batch translate
            mock_translator.translate_batch.return_value = ["RESULT2", "RESULT3"]

            results = cached.translate_batch(
                ["text1", "text2", "text3"],
                target_lang="EN"
            )

            assert results == ["CACHED_RESULT", "RESULT2", "RESULT3"]
            # Should only translate uncached texts
            mock_translator.translate_batch.assert_called_once()

    def test_cache_disabled(self):
        """Test cached translator with caching disabled."""
        mock_translator = Mock()
        mock_translator.translate_text.return_value = "RESULT"

        cached = CachedTranslator(mock_translator, enable_cache=False)

        result1 = cached.translate_text("test", target_lang="EN")
        result2 = cached.translate_text("test", target_lang="EN")

        # Both should call translator (no caching)
        assert mock_translator.translate_text.call_count == 2

    def test_async_translate_text_cache_hit(self):
        """Async translation should use cache when available."""
        mock_translator = Mock()
        mock_translator.translate_text_async = AsyncMock(return_value="RESULT")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)
            cache.set("hello", "CACHED", "NL", "EN")

            cached = CachedTranslator(mock_translator, cache=cache)
            result = asyncio.run(cached.translate_text_async("hello", target_lang="EN"))

            assert result == "CACHED"
            mock_translator.translate_text_async.assert_not_called()

    def test_async_translate_batch_partial_cache(self):
        """Async batch translation should only call translator for uncached entries."""
        mock_translator = Mock()
        mock_translator.translate_batch_async = AsyncMock(return_value=["NEW2", "NEW3"])

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache = TranslationCache(cache_file=str(cache_file), enable_persistence=False)
            cache.set("text1", "CACHED1", "NL", "EN")

            cached = CachedTranslator(mock_translator, cache=cache)
            results = asyncio.run(
                cached.translate_batch_async(
                    ["text1", "text2", "text3"],
                    target_lang="EN",
                )
            )

            assert results == ["CACHED1", "NEW2", "NEW3"]
            mock_translator.translate_batch_async.assert_awaited_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
