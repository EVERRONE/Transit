"""Memory optimization utilities for large document processing."""

import logging
import gc
import sys
from typing import Iterator, Any, Optional, Dict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """
    Monitor memory usage during document processing.

    Tracks memory consumption and provides warnings when thresholds are exceeded.
    """

    def __init__(self, warning_threshold_mb: int = 500, critical_threshold_mb: int = 1000):
        """
        Initialize memory monitor.

        Args:
            warning_threshold_mb: Memory threshold for warnings (MB)
            critical_threshold_mb: Memory threshold for critical alerts (MB)
        """
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        self.peak_memory_mb = 0
        self.baseline_memory_mb = 0

        self._record_baseline()

        logger.info(
            f"Memory monitor initialized: "
            f"warning={warning_threshold_mb}MB, "
            f"critical={critical_threshold_mb}MB"
        )

    def _record_baseline(self):
        """Record baseline memory usage."""
        try:
            import psutil
            process = psutil.Process()
            self.baseline_memory_mb = process.memory_info().rss / 1024 / 1024
            logger.debug(f"Baseline memory: {self.baseline_memory_mb:.1f}MB")
        except ImportError:
            logger.warning("psutil not available, memory monitoring disabled")
            self.baseline_memory_mb = 0

    def get_current_memory_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in MB, or 0 if psutil unavailable
        """
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def get_memory_delta_mb(self) -> float:
        """
        Get memory usage delta from baseline.

        Returns:
            Memory increase in MB
        """
        current = self.get_current_memory_mb()
        return current - self.baseline_memory_mb if self.baseline_memory_mb > 0 else 0.0

    def check_memory(self) -> Optional[str]:
        """
        Check current memory usage against thresholds.

        Returns:
            Warning message if threshold exceeded, None otherwise
        """
        delta = self.get_memory_delta_mb()

        if delta <= 0:
            return None

        # Update peak
        if delta > self.peak_memory_mb:
            self.peak_memory_mb = delta

        # Check thresholds
        if delta >= self.critical_threshold_mb:
            msg = f"CRITICAL: Memory usage {delta:.1f}MB exceeds critical threshold {self.critical_threshold_mb}MB"
            logger.critical(msg)
            return msg
        elif delta >= self.warning_threshold_mb:
            msg = f"WARNING: Memory usage {delta:.1f}MB exceeds warning threshold {self.warning_threshold_mb}MB"
            logger.warning(msg)
            return msg

        return None

    def log_stats(self):
        """Log memory usage statistics."""
        current = self.get_memory_delta_mb()

        if current > 0:
            logger.info(
                f"Memory stats: current={current:.1f}MB, "
                f"peak={self.peak_memory_mb:.1f}MB, "
                f"baseline={self.baseline_memory_mb:.1f}MB"
            )


class StreamingDocumentIterator:
    """
    Iterator for processing document elements with minimal memory footprint.

    Yields elements one at a time and clears references after processing.
    """

    def __init__(self, doc, memory_monitor: Optional[MemoryMonitor] = None):
        """
        Initialize streaming iterator.

        Args:
            doc: Document to iterate
            memory_monitor: Optional memory monitor
        """
        self.doc = doc
        self.memory_monitor = memory_monitor
        self.processed_count = 0
        self.gc_interval = 100  # Run garbage collection every N elements

    def iter_paragraphs(self) -> Iterator[Any]:
        """
        Iterate over paragraphs with memory management.

        Yields:
            Paragraph objects
        """
        for i, para in enumerate(self.doc.paragraphs):
            yield para

            self.processed_count += 1

            # Periodic garbage collection
            if self.processed_count % self.gc_interval == 0:
                self._gc_checkpoint()

    def iter_tables(self) -> Iterator[Any]:
        """
        Iterate over tables with memory management.

        Yields:
            Table objects
        """
        for i, table in enumerate(self.doc.tables):
            yield table

            self.processed_count += 1

            if self.processed_count % self.gc_interval == 0:
                self._gc_checkpoint()

    def iter_inner_content(self) -> Iterator[Any]:
        """
        Iterate over all content with memory management.

        Yields:
            Paragraph or Table objects in document order
        """
        for block in self.doc.iter_inner_content():
            yield block

            self.processed_count += 1

            if self.processed_count % self.gc_interval == 0:
                self._gc_checkpoint()

    def _gc_checkpoint(self):
        """Run garbage collection and check memory."""
        gc.collect()

        if self.memory_monitor:
            warning = self.memory_monitor.check_memory()
            if warning:
                logger.warning(f"Memory checkpoint at element {self.processed_count}: {warning}")


@contextmanager
def memory_optimized_processing(
    warning_threshold_mb: int = 500,
    critical_threshold_mb: int = 1000,
    enable_gc: bool = True
):
    """
    Context manager for memory-optimized document processing.

    Args:
        warning_threshold_mb: Warning threshold in MB
        critical_threshold_mb: Critical threshold in MB
        enable_gc: Enable aggressive garbage collection

    Yields:
        MemoryMonitor instance
    """
    monitor = MemoryMonitor(warning_threshold_mb, critical_threshold_mb)

    # Enable aggressive GC if requested
    if enable_gc:
        old_threshold = gc.get_threshold()
        gc.set_threshold(100, 5, 5)  # More aggressive
        logger.debug("Enabled aggressive garbage collection")

    try:
        yield monitor
    finally:
        # Restore GC settings
        if enable_gc:
            gc.set_threshold(*old_threshold)
            logger.debug("Restored garbage collection settings")

        # Final cleanup
        gc.collect()
        monitor.log_stats()


class ChunkedDocumentProcessor:
    """
    Process large documents in chunks to reduce memory usage.

    Saves intermediate results and combines them at the end.
    """

    def __init__(self, chunk_size: int = 50):
        """
        Initialize chunked processor.

        Args:
            chunk_size: Number of elements to process per chunk
        """
        self.chunk_size = chunk_size
        logger.info(f"Initialized chunked processor with chunk_size={chunk_size}")

    def process_in_chunks(
        self,
        elements: list,
        process_func,
        combine_func=None
    ) -> Any:
        """
        Process elements in chunks.

        Args:
            elements: List of elements to process
            process_func: Function to process each chunk
            combine_func: Optional function to combine chunk results

        Returns:
            Combined result or list of chunk results
        """
        if not elements:
            return [] if combine_func is None else combine_func([])

        num_chunks = (len(elements) + self.chunk_size - 1) // self.chunk_size
        logger.info(f"Processing {len(elements)} elements in {num_chunks} chunks")

        chunk_results = []

        for i in range(0, len(elements), self.chunk_size):
            chunk = elements[i:i + self.chunk_size]
            chunk_num = i // self.chunk_size + 1

            logger.debug(f"Processing chunk {chunk_num}/{num_chunks} ({len(chunk)} elements)")

            try:
                result = process_func(chunk)
                chunk_results.append(result)
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {e}")
                raise

            # Garbage collection after each chunk
            gc.collect()

        # Combine results if function provided
        if combine_func:
            logger.debug("Combining chunk results")
            return combine_func(chunk_results)

        return chunk_results


class MemoryEfficientCache:
    """
    Memory-efficient cache with size limits.

    Automatically evicts old entries when size limit is reached.
    """

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        """
        Initialize memory-efficient cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Approximate maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.cache: Dict[str, Any] = {}
        self.access_order: list = []

        logger.info(f"Initialized cache: max_size={max_size}, max_memory={max_memory_mb}MB")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        value = self.cache.get(key)

        if value is not None:
            # Update access order (LRU)
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

        return value

    def set(self, key: str, value: Any):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Check if we need to evict
        if key not in self.cache and len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[key] = value

        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def _evict_oldest(self):
        """Evict oldest entry from cache."""
        if self.access_order:
            oldest_key = self.access_order.pop(0)
            if oldest_key in self.cache:
                del self.cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.access_order.clear()
        gc.collect()
        logger.debug("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with stats
        """
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size * 100 if self.max_size > 0 else 0
        }

    def __len__(self) -> int:
        """Get number of cached entries."""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """Check if key is in cache."""
        return key in self.cache
