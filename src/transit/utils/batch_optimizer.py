"""Batch processing optimizer for translation APIs."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class BatchOptimizer:
    """
    Optimizes translation batches for maximum efficiency.

    Groups texts intelligently based on:
    - API batch size limits
    - Total character limits
    - Context similarity
    """

    def __init__(
        self,
        max_batch_size: int = 50,
        max_chars_per_batch: int = 50000,
        enable_context_grouping: bool = True
    ):
        """
        Initialize batch optimizer.

        Args:
            max_batch_size: Maximum number of texts per batch
            max_chars_per_batch: Maximum total characters per batch
            enable_context_grouping: Group similar contexts together
        """
        self.max_batch_size = max_batch_size
        self.max_chars_per_batch = max_chars_per_batch
        self.enable_context_grouping = enable_context_grouping

        logger.info(
            f"Initialized batch optimizer: "
            f"max_batch_size={max_batch_size}, "
            f"max_chars={max_chars_per_batch}, "
            f"context_grouping={enable_context_grouping}"
        )

    def optimize_batches(
        self,
        texts: List[str],
        contexts: Optional[List[str]] = None
    ) -> List[List[int]]:
        """
        Optimize text grouping into batches.

        Args:
            texts: List of texts to batch
            contexts: Optional list of contexts (same length as texts)

        Returns:
            List of batches, where each batch is a list of indices into texts
        """
        if not texts:
            return []

        if contexts and len(contexts) != len(texts):
            logger.warning("Contexts length mismatch, ignoring contexts")
            contexts = None

        # Create items with indices
        items = [
            {
                'index': i,
                'text': text,
                'length': len(text),
                'context': contexts[i] if contexts else None
            }
            for i, text in enumerate(texts)
        ]

        # Group by context if enabled
        if self.enable_context_grouping and contexts:
            batches = self._optimize_with_context_grouping(items)
        else:
            batches = self._optimize_by_size(items)

        logger.info(f"Optimized {len(texts)} texts into {len(batches)} batches")

        # Return indices only
        return [[item['index'] for item in batch] for batch in batches]

    def _optimize_by_size(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Optimize batches by size only.

        Uses greedy bin packing algorithm.

        Args:
            items: List of item dictionaries

        Returns:
            List of batches (each batch is list of items)
        """
        batches = []
        current_batch = []
        current_chars = 0

        for item in items:
            # Check if adding this item would exceed limits
            would_exceed_size = len(current_batch) >= self.max_batch_size
            would_exceed_chars = current_chars + item['length'] > self.max_chars_per_batch

            if current_batch and (would_exceed_size or would_exceed_chars):
                # Start new batch
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

            # Check if single item exceeds character limit
            if item['length'] > self.max_chars_per_batch:
                logger.warning(
                    f"Text at index {item['index']} ({item['length']} chars) "
                    f"exceeds max_chars_per_batch ({self.max_chars_per_batch}), "
                    f"creating single-item batch"
                )
                batches.append([item])
                continue

            current_batch.append(item)
            current_chars += item['length']

        # Add final batch
        if current_batch:
            batches.append(current_batch)

        return batches

    def _optimize_with_context_grouping(
        self,
        items: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Optimize batches with context grouping.

        Groups items with same context together for better translation quality.

        Args:
            items: List of item dictionaries

        Returns:
            List of batches (each batch is list of items)
        """
        # Group by context
        context_groups = defaultdict(list)

        for item in items:
            context = item['context'] or 'default'
            context_groups[context].append(item)

        logger.debug(f"Grouped into {len(context_groups)} context groups")

        # Optimize each context group separately
        all_batches = []

        for context, group_items in context_groups.items():
            context_batches = self._optimize_by_size(group_items)
            all_batches.extend(context_batches)

        return all_batches

    def estimate_batch_count(
        self,
        texts: List[str],
        contexts: Optional[List[str]] = None
    ) -> int:
        """
        Estimate number of batches without full optimization.

        Useful for progress estimation.

        Args:
            texts: List of texts
            contexts: Optional contexts

        Returns:
            Estimated number of batches
        """
        if not texts:
            return 0

        total_chars = sum(len(text) for text in texts)
        total_texts = len(texts)

        # Estimate based on character limit
        char_based_estimate = (total_chars + self.max_chars_per_batch - 1) // self.max_chars_per_batch

        # Estimate based on batch size limit
        size_based_estimate = (total_texts + self.max_batch_size - 1) // self.max_batch_size

        # Take the larger estimate
        return max(char_based_estimate, size_based_estimate)

    def get_batch_stats(self, batches: List[List[int]], texts: List[str]) -> Dict[str, Any]:
        """
        Get statistics about batches.

        Args:
            batches: List of batches (lists of indices)
            texts: Original list of texts

        Returns:
            Dictionary with statistics
        """
        if not batches:
            return {
                'total_batches': 0,
                'total_texts': 0,
                'avg_batch_size': 0,
                'avg_batch_chars': 0,
                'max_batch_size': 0,
                'max_batch_chars': 0,
                'min_batch_size': 0,
                'min_batch_chars': 0
            }

        batch_sizes = [len(batch) for batch in batches]
        batch_chars = [
            sum(len(texts[idx]) for idx in batch)
            for batch in batches
        ]

        return {
            'total_batches': len(batches),
            'total_texts': sum(batch_sizes),
            'avg_batch_size': sum(batch_sizes) / len(batches),
            'avg_batch_chars': sum(batch_chars) / len(batches),
            'max_batch_size': max(batch_sizes),
            'max_batch_chars': max(batch_chars),
            'min_batch_size': min(batch_sizes),
            'min_batch_chars': min(batch_chars)
        }


class SmartBatchTranslator:
    """
    Wrapper that adds smart batching to any translator.

    Automatically batches translation requests for optimal performance.
    """

    def __init__(
        self,
        translator,
        batch_optimizer: Optional[BatchOptimizer] = None,
        auto_batch_threshold: int = 5
    ):
        """
        Initialize smart batch translator.

        Args:
            translator: Underlying translator
            batch_optimizer: Optional custom batch optimizer
            auto_batch_threshold: Minimum texts to trigger auto-batching
        """
        self.translator = translator
        self.batch_optimizer = batch_optimizer or BatchOptimizer()
        self.auto_batch_threshold = auto_batch_threshold

        logger.info(f"Initialized smart batch translator with threshold={auto_batch_threshold}")

    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None
    ) -> str:
        """
        Translate single text (delegates to underlying translator).

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code
            preserve_formatting: Preserve formatting
            context: Optional context

        Returns:
            Translated text
        """
        return self.translator.translate_text(
            text,
            target_lang=target_lang,
            source_lang=source_lang,
            preserve_formatting=preserve_formatting,
            context=context
        )

    def translate_multiple(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        contexts: Optional[List[str]] = None
    ) -> List[str]:
        """
        Translate multiple texts with smart batching.

        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            preserve_formatting: Preserve formatting
            contexts: Optional list of contexts

        Returns:
            List of translated texts in same order
        """
        if not texts:
            return []

        # Check if batching is beneficial
        if len(texts) < self.auto_batch_threshold:
            logger.debug(f"Text count ({len(texts)}) below threshold, translating individually")
            return [
                self.translate_text(
                    text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    context=contexts[i] if contexts else None
                )
                for i, text in enumerate(texts)
            ]

        # Optimize batches
        batch_indices = self.batch_optimizer.optimize_batches(texts, contexts)

        logger.info(f"Translating {len(texts)} texts in {len(batch_indices)} optimized batches")

        # Execute batches
        results = [None] * len(texts)

        for batch_idx, indices in enumerate(batch_indices):
            batch_texts = [texts[i] for i in indices]

            # Check if translator supports batch translation
            if hasattr(self.translator, 'translate_batch'):
                # Use native batch translation
                batch_contexts = [contexts[i] if contexts else None for i in indices] if contexts else None
                batch_results = self.translator.translate_batch(
                    batch_texts,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    batch_context=batch_contexts[0] if batch_contexts else None
                )
            else:
                # Fallback to individual translation
                logger.warning("Translator doesn't support batch translation, falling back to individual")
                batch_results = [
                    self.translator.translate_text(
                        text,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting
                    )
                    for text in batch_texts
                ]

            # Map results back to original indices
            for i, result in zip(indices, batch_results):
                results[i] = result

            logger.debug(f"Completed batch {batch_idx + 1}/{len(batch_indices)}")

        return results

    # Delegate attribute access to underlying translator
    def __getattr__(self, name):
        """Forward unknown attributes to underlying translator."""
        return getattr(self.translator, name)
