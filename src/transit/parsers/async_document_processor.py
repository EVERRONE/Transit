"""Async document processor for improved performance on large documents."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from docx import Document

from transit.core.exceptions import CorruptDocumentError
from transit.parsers.context_collection import collect_document_contexts, ParagraphContext
from transit.parsers.document_processor import DocumentProcessor
from transit.translators.async_translator import AsyncTranslatorWrapper
from transit.utils.batch_optimizer import BatchOptimizer

logger = logging.getLogger(__name__)


@dataclass
class TranslationTask:
    """Async translation task tied to a specific paragraph context."""

    context: ParagraphContext
    text: str
    target_lang: str
    result: Optional[str] = None
    index: int = 0


class AsyncDocumentProcessor(DocumentProcessor):
    """
    Async version of DocumentProcessor for better performance on large documents.

    Collects all paragraphs up-front, translates them concurrently, and then applies
    the translations while preserving the original structure.
    """

    def __init__(self, translator, max_concurrent: Optional[int] = None):
        recommended = getattr(translator, "recommended_concurrency", None)
        resolved_concurrency = max_concurrent or recommended or 10
        self.async_translator = AsyncTranslatorWrapper(translator, max_concurrent=resolved_concurrency)
        super().__init__(self.async_translator)
        self.max_concurrent = resolved_concurrency
        batch_char_budget = getattr(self.async_translator.translator, "batch_char_budget", None)
        self.max_batch_chars = batch_char_budget or getattr(self.async_translator.translator, "MAX_BATCH_CHARS", 12000)
        batch_size_hint = getattr(self.async_translator.translator, "max_batch_size_hint", None)
        self.max_batch_size = batch_size_hint or max(10, self.max_concurrent * 8)
        logger.info(
            "Initialized async document processor (max_concurrent=%d, batch_chars=%d, batch_size=%d)",
            self.max_concurrent,
            self.max_batch_chars,
            self.max_batch_size,
        )

    async def translate_document_async(
        self,
        input_path: str,
        output_path: str,
        target_lang: str,
        show_progress: bool = False  # Retained for signature compatibility
    ) -> None:
        try:
            doc = Document(input_path)
            logger.info("Loaded document: %s", input_path)
        except Exception as exc:
            raise CorruptDocumentError(f"Cannot load document: {exc}") from exc

        if self.supports_context:
            context_summary = self._extract_document_context(doc)
            self.translator.set_document_context(context_summary)
            logger.info("Document context set for intelligent translation")

        traversal = collect_document_contexts(doc)
        contexts = traversal.contexts

        for warning in traversal.warnings:
            logger.warning(warning)

        tasks = self._create_translation_tasks(contexts, target_lang)
        logger.info("Executing %d asynchronous translation tasks...", len(tasks))

        await self._execute_translation_tasks(tasks)

        try:
            doc.save(output_path)
            logger.info("Saved translated document: %s", output_path)
        except Exception as exc:
            raise CorruptDocumentError(f"Cannot save document: {exc}") from exc

        self.async_translator.log_stats()

    def _create_translation_tasks(self, contexts: List[ParagraphContext], target_lang: str) -> List[TranslationTask]:
        tasks: List[TranslationTask] = []

        for context in contexts:
            paragraph = context.paragraph
            text = paragraph.text
            if not text or not text.strip():
                continue

            task_index = len(tasks)
            tasks.append(
                TranslationTask(
                    context=context,
                    text=text,
                    target_lang=target_lang,
                    index=task_index,
                )
            )

        return tasks

    async def _execute_translation_tasks(self, tasks: List[TranslationTask]) -> None:
        if not tasks:
            return

        batches = self._plan_batches(tasks)

        async def _translate_batch(batch: List[TranslationTask]) -> List[str]:
            if not batch:
                return []

            target_lang = batch[0].target_lang
            if any(task.target_lang != target_lang for task in batch):
                raise ValueError("All tasks in a batch must share the same target language")

            # Single-item batches can leverage streaming path for lower latency.
            if len(batch) == 1:
                single_task = batch[0]
                try:
                    translation = await self.async_translator.translate_text_async(
                        single_task.text,
                        target_lang=single_task.target_lang,
                        source_lang="NL",
                        preserve_formatting=True,
                        context=None,
                    )
                except Exception as exc:
                    logger.error("Single translation failed: %s", exc)
                    translation = single_task.text
                return [translation]

            texts = [task.text for task in batch]

            try:
                results = await self.async_translator.translate_batch_async(
                    texts,
                    target_lang=target_lang,
                    source_lang="NL",
                    preserve_formatting=True,
                )
            except Exception as exc:
                logger.error("Batch translation failed: %s", exc)
                results = [task.text for task in batch]

            if len(results) != len(batch):
                logger.warning(
                    "Batch result length mismatch (%d vs %d); using original text for this batch.",
                    len(results),
                    len(batch),
                )
                results = [task.text for task in batch]

            return results

        pending: Dict[asyncio.Task, List[TranslationTask]] = {}
        for batch in batches:
            pending[asyncio.create_task(_translate_batch(batch))] = batch

        ready_tasks: Dict[int, TranslationTask] = {}
        next_index_to_apply = 0
        total_tasks = len(tasks)

        while pending:
            done, _ = await asyncio.wait(
                pending.keys(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            for completed in done:
                batch = pending.pop(completed)
                try:
                    results = completed.result()
                except Exception as exc:
                    logger.error("Batch translation raised unexpectedly: %s", exc)
                    results = [task.text for task in batch]

                if len(results) != len(batch):
                    logger.warning(
                        "Batch result length mismatch (%d vs %d); using original text for this batch.",
                        len(results),
                        len(batch),
                    )
                    results = [task.text for task in batch]

                for task_obj, translated in zip(batch, results):
                    task_obj.result = translated
                    ready_tasks[task_obj.index] = task_obj

            while next_index_to_apply < total_tasks and next_index_to_apply in ready_tasks:
                ready_task = ready_tasks.pop(next_index_to_apply)
                translated_text = ready_task.result if ready_task.result is not None else ready_task.text
                self._apply_translated_text(ready_task.context.paragraph, translated_text)
                next_index_to_apply += 1

        # Apply any stragglers (should be no-op but keeps safety).
        while next_index_to_apply < total_tasks and next_index_to_apply in ready_tasks:
            ready_task = ready_tasks.pop(next_index_to_apply)
            translated_text = ready_task.result if ready_task.result is not None else ready_task.text
            self._apply_translated_text(ready_task.context.paragraph, translated_text)
            next_index_to_apply += 1

    def _plan_batches(self, tasks: List[TranslationTask]) -> List[List[TranslationTask]]:
        if not tasks:
            return []

        texts = [task.text for task in tasks]
        locations = [task.context.location for task in tasks]

        optimizer = BatchOptimizer(
            max_batch_size=self.max_batch_size,
            max_chars_per_batch=self.max_batch_chars,
            enable_context_grouping=True,
        )

        batches_indices = optimizer.optimize_batches(texts, contexts=locations)
        # Prioritize longest batches first to avoid tail latency.
        batches_indices.sort(
            key=lambda batch: sum(len(texts[idx]) for idx in batch),
            reverse=True,
        )

        return [[tasks[idx] for idx in batch] for batch in batches_indices]

    def translate_document(
        self,
        input_path: str,
        output_path: str,
        target_lang: str,
        show_progress: bool = False
    ) -> None:
        asyncio.run(
            self.translate_document_async(
                input_path=input_path,
                output_path=output_path,
                target_lang=target_lang,
                show_progress=show_progress,
            )
        )

    def close(self):
        self.async_translator.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
