"""Async translator wrapper for improved performance on large documents."""

import asyncio
import inspect
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AsyncTranslatorWrapper:
    """Async wrapper for translators to enable concurrent translation."""

    def __init__(self, translator, max_concurrent: int = 10):
        self.translator = translator
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor: Optional[ThreadPoolExecutor] = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "total_characters": 0,
        }
        logger.info("Initialized async translator with max_concurrent=%d", max_concurrent)

    def _ensure_executor(self) -> ThreadPoolExecutor:
        """Lazily create the threadpool for legacy sync translators."""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        return self.executor

    def _is_coroutine_method(self, name: str) -> bool:
        """Check if the wrapped translator exposes an async method on its class."""
        method = getattr(type(self.translator), name, None)
        return method is not None and inspect.iscoroutinefunction(method)

    async def translate_text_async(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None,
    ) -> str:
        async with self.semaphore:
            self.stats["total_requests"] += 1
            self.stats["total_characters"] += len(text)
            start_time = time.time()

            try:
                if self._is_coroutine_method("translate_text_async"):
                    result = await self.translator.translate_text_async(
                        text,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        context=context,
                    )
                else:
                    loop = asyncio.get_running_loop()
                    executor = self._ensure_executor()
                    result = await loop.run_in_executor(
                        executor,
                        lambda: self.translator.translate_text(
                            text,
                            target_lang=target_lang,
                            source_lang=source_lang,
                            preserve_formatting=preserve_formatting,
                            context=context,
                        ),
                    )

                elapsed = time.time() - start_time
                self.stats["total_time"] += elapsed
                self.stats["successful_requests"] += 1
                logger.debug("Translated %d chars in %.2fs", len(text), elapsed)
                return result
            except Exception as exc:
                self.stats["failed_requests"] += 1
                logger.error("Async translation failed: %s", exc)
                raise

    async def translate_batch_async(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        batch_context: Optional[str] = None,
    ) -> List[str]:
        if not texts:
            return []

        if self._is_coroutine_method("translate_batch_async"):
            async with self.semaphore:
                self.stats["total_requests"] += 1
                total_chars = sum(len(text or "") for text in texts)
                self.stats["total_characters"] += total_chars
                start_time = time.time()
                try:
                    result = await self.translator.translate_batch_async(
                        texts,
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        batch_context=batch_context,
                    )
                    elapsed = time.time() - start_time
                    self.stats["total_time"] += elapsed
                    self.stats["successful_requests"] += 1
                    logger.debug(
                        "Batch translated %d texts (%d chars) in %.2fs",
                        len(texts),
                        total_chars,
                        elapsed,
                    )
                    return result
                except Exception as exc:
                    self.stats["failed_requests"] += 1
                    logger.error("Batch translation failed, falling back to individual requests: %s", exc)
                    # Fall through to per-text fallback
        elif hasattr(self.translator, "translate_batch"):
            async with self.semaphore:
                self.stats["total_requests"] += 1
                total_chars = sum(len(text or "") for text in texts)
                self.stats["total_characters"] += total_chars
                start_time = time.time()
                loop = asyncio.get_running_loop()
                try:
                    executor = self._ensure_executor()
                    result = await loop.run_in_executor(
                        executor,
                        lambda: self.translator.translate_batch(
                            texts,
                            target_lang=target_lang,
                            source_lang=source_lang,
                            preserve_formatting=preserve_formatting,
                            batch_context=batch_context,
                        ),
                    )
                    elapsed = time.time() - start_time
                    self.stats["total_time"] += elapsed
                    self.stats["successful_requests"] += 1
                    logger.debug(
                        "Batch translated %d texts (%d chars) in %.2fs",
                        len(texts),
                        total_chars,
                        elapsed,
                    )
                    return result
                except Exception as exc:
                    self.stats["failed_requests"] += 1
                    logger.error("Batch translation failed, falling back to individual requests: %s", exc)
                    # Fall through to per-text fallback

        logger.info("Starting fallback async batch translation of %d texts", len(texts))
        tasks = [
            self.translate_text_async(
                text,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                context=batch_context,
            )
            for text in texts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        translated_texts: List[str] = []
        for index, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Translation %d failed during fallback: %s", index, result)
                translated_texts.append(texts[index])
            else:
                translated_texts.append(result)
        return translated_texts

    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None,
    ) -> str:
        return asyncio.run(
            self.translate_text_async(
                text,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                context=context,
            )
        )

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        batch_context: Optional[str] = None,
    ) -> List[str]:
        return asyncio.run(
            self.translate_batch_async(
                texts,
                target_lang=target_lang,
                source_lang=source_lang,
                preserve_formatting=preserve_formatting,
                batch_context=batch_context,
            )
        )

    def get_stats(self) -> Dict[str, Any]:
        stats = self.stats.copy()
        if stats["successful_requests"] > 0:
            stats["avg_time_per_request"] = stats["total_time"] / stats["successful_requests"]
            stats["avg_chars_per_request"] = stats["total_characters"] / stats["successful_requests"]
        else:
            stats["avg_time_per_request"] = 0.0
            stats["avg_chars_per_request"] = 0
        stats["success_rate"] = (
            stats["successful_requests"] / stats["total_requests"] * 100
            if stats["total_requests"] > 0
            else 0.0
        )
        return stats

    def log_stats(self) -> None:
        stats = self.get_stats()
        logger.info(
            "Async translation stats: %d/%d requests successful (%.1f%%), avg time: %.2fs, total chars: %d",
            stats["successful_requests"],
            stats["total_requests"],
            stats["success_rate"],
            stats["avg_time_per_request"],
            stats["total_characters"],
        )

    def reset_stats(self) -> None:
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "total_characters": 0,
        }

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying translator."""
        return getattr(self.translator, name)

    def close(self) -> None:
        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Async translator threadpool closed")
        else:
            logger.info("Async translator closed (no threadpool needed)")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
