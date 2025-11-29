"""OpenAI translator implementation with context awareness."""

from __future__ import annotations

import asyncio
import time
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import APIError, AsyncOpenAI, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential

from transit.core.exceptions import APIAuthenticationError

logger = logging.getLogger(__name__)


class OpenAITranslator:
    """OpenAI GPT-4o powered translator with context awareness."""

    LANG_NAMES = {
        "EN-US": "American English",
        "EN-GB": "British English",
        "DE": "German",
        "FR": "French",
        "ES": "Spanish",
        "IT": "Italian",
        "PT": "Portuguese",
        "PL": "Polish",
        "RU": "Russian",
        "JA": "Japanese",
        "ZH": "Chinese",
        "KO": "Korean",
        "NL": "Dutch",
    }

    MAX_BATCH_CHARS = 50_000
    STREAM_SINGLE_REQUESTS = True
    MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
        "default": {
            "batch_char_budget": 75_000,
            "recommended_concurrency": 10,
            "max_batch_size": 80,
        },
        "gpt-4o": {
            "batch_char_budget": 180_000,
            "recommended_concurrency": 12,
            "max_batch_size": 120,
        },
        "gpt-4o-mini": {
            "batch_char_budget": 120_000,
            "recommended_concurrency": 16,
            "max_batch_size": 160,
        },
        "gpt-4o-mini-translation": {
            "batch_char_budget": 180_000,
            "recommended_concurrency": 18,
            "max_batch_size": 200,
        },
    }

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        if not api_key:
            raise APIAuthenticationError("OpenAI API key is required")

        try:
            self.client = AsyncOpenAI(api_key=api_key)
        except Exception as exc:
            if getattr(exc, "status_code", None) == 401:
                raise APIAuthenticationError("Invalid OpenAI API key") from exc
            raise

        self.model = model
        self.document_context: Optional[str] = None
        self._resolve_capabilities(model)

    def _resolve_capabilities(self, model: str) -> None:
        caps = self.MODEL_CAPABILITIES.get(model)
        if caps is None and ":" in model:
            caps = self.MODEL_CAPABILITIES.get(model.split(":")[0])
        if caps is None:
            caps = self.MODEL_CAPABILITIES["default"]

        self.batch_char_budget = caps.get("batch_char_budget", self.MAX_BATCH_CHARS)
        self.recommended_concurrency = caps.get("recommended_concurrency", 10)
        self.max_batch_size_hint = caps.get("max_batch_size", 80)

    @staticmethod
    def _run_sync(coro):
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def set_document_context(self, context: str) -> None:
        self.document_context = context
        logger.info("Document context set: %s...", context[:100])

    def _build_system_prompt(self, target_lang: str, source_lang: str = "NL") -> str:
        target_name = self.LANG_NAMES.get(target_lang, target_lang)
        source_name = self.LANG_NAMES.get(source_lang, source_lang)

        prompt = f"""You are a professional document translator specializing in translating {source_name} to {target_name}.

Your task is to provide HIGH-QUALITY, CONTEXT-AWARE translations that:

1. **Preserve meaning perfectly** - Capture nuances, idioms, and intent
2. **Handle complex elements intelligently**:
   - Abbreviations (e.g., "b.v." → "for example", "m.b.t." → "regarding")
   - Technical terms (keep or translate based on context)
   - Proper nouns (keep original, unless standard translation exists)
   - Idioms (translate to equivalent idiom in target language)
   - Dates and numbers (adapt to target locale conventions)
3. **Maintain formality level** - Match the tone (formal/informal) of the source
4. **Preserve formatting markers** - Keep any XML-like tags intact
5. **Handle ambiguity** - Use context to disambiguate

CRITICAL RULES:
- Return ONLY the translated text, no explanations
- Preserve exact whitespace (spaces, line breaks, tabs)
- Do NOT translate text that is already in the target language
- If unsure, prefer literal translation over interpretation"""

        if self.document_context:
            prompt += f"\n\nDOCUMENT CONTEXT:\n{self.document_context}"

        return prompt

    @retry(wait=wait_exponential(min=1, max=60), stop=stop_after_attempt(5))
    def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None,
    ) -> str:
        if not text or not text.strip():
            return text

        try:
            return self._run_sync(
                self.translate_text_async(
                    text=text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    context=context,
                )
            )
        except RateLimitError:
            logger.warning("Rate limit hit during translate_text, retrying...")
            raise
        except Exception as exc:
            logger.error("Unexpected error translating text: %s", exc)
            return text

    def translate_batch(
        self,
        texts: List[str],
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        batch_context: Optional[str] = None,
    ) -> List[str]:
        if not texts:
            return []

        try:
            return self._run_sync(
                self.translate_batch_async(
                    texts=texts,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    batch_context=batch_context,
                )
            )
        except RateLimitError:
            logger.warning("Rate limit hit during translate_batch, retrying...")
            raise
        except Exception as exc:
            logger.error("Batch translation failed (%s). Falling back to individual translation.", exc)
            result = list(texts)
            for idx, text in enumerate(texts):
                result[idx] = self.translate_text(
                    text,
                    target_lang=target_lang,
                    source_lang=source_lang,
                    preserve_formatting=preserve_formatting,
                    context=batch_context,
                )
            return result

    def translate_paragraph_with_context(
        self,
        paragraph_text: str,
        target_lang: str,
        source_lang: str = "NL",
        surrounding_context: Optional[str] = None,
    ) -> str:
        context_note = None
        if surrounding_context:
            context_note = f"Surrounding text for context: {surrounding_context[:200]}..."

        return self.translate_text(
            paragraph_text,
            target_lang=target_lang,
            source_lang=source_lang,
            context=context_note,
        )

    async def translate_text_async(
        self,
        text: str,
        target_lang: str,
        source_lang: str = "NL",
        preserve_formatting: bool = True,
        context: Optional[str] = None,
    ) -> str:
        if not text or not text.strip():
            return text

        user_message = f"Translate the following text to {self.LANG_NAMES.get(target_lang, target_lang)}:\n\n{text}"
        if context:
            user_message = f"Context: {context}\n\n{user_message}"

        messages = [
            {"role": "system", "content": self._build_system_prompt(target_lang, source_lang)},
            {"role": "user", "content": user_message},
        ]

        try:
            response_text = await self._execute_response(
                messages,
                stream=self.STREAM_SINGLE_REQUESTS,
            )
            if response_text is None:
                raise ValueError("Empty response from OpenAI")
            return response_text
        except RateLimitError:
            raise
        except APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise
        except Exception as exc:
            logger.error("Unexpected error translating text asynchronously: %s", exc)
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

        non_empty_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts

        batch_payload, id_mapping = self._build_batch_payload(
            non_empty_texts,
            non_empty_indices,
            target_lang,
            source_lang,
            batch_context,
        )

        try:
            raw_content = await self._execute_response(
                batch_payload["messages"],
                stream=False,
                response_format={"type": "json_object"},
            )

            parsed = self._parse_batch_response(raw_content)
            if parsed is None or len(parsed) != len(non_empty_texts):
                raise ValueError("Batch response missing items or count mismatch")

            result = list(texts)
            for local_id, original_index in id_mapping:
                translation = parsed.get(local_id)
                if translation is None:
                    raise ValueError(f"Missing translation for id {local_id}")
                result[original_index] = translation

            return result
        except RateLimitError:
            raise
        except Exception as exc:
            logger.error("Batch translation failed (%s). Falling back to individual translation.", exc)
            result = list(texts)
            for original_index in non_empty_indices:
                try:
                    result[original_index] = await self.translate_text_async(
                        texts[original_index],
                        target_lang=target_lang,
                        source_lang=source_lang,
                        preserve_formatting=preserve_formatting,
                        context=batch_context,
                    )
                except Exception:
                    result[original_index] = texts[original_index]
            return result

    async def _execute_response(
        self,
        messages: List[Dict[str, str]],
        *,
        stream: bool = False,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        input_payload = self._messages_to_responses_input(messages)

        if stream:
            stream_handle = await self.client.responses.create(
                model=self.model,
                input=input_payload,
                response_format=response_format,
                stream=True,
            )
            return await self._consume_stream(stream_handle)

        response = await self.client.responses.create(
            model=self.model,
            input=input_payload,
            response_format=response_format,
        )
        return self._extract_output_text(response)

    async def _consume_stream(self, stream) -> str:
        chunks: List[str] = []
        async for event in stream:
            event_type = getattr(event, "type", "")
            if event_type == "response.output_text.delta":
                delta = getattr(event, "delta", "")
                if delta:
                    chunks.append(delta)
            elif event_type == "response.error":
                error = getattr(event, "error", "Unknown error")
                raise RuntimeError(error)
            elif event_type == "response.completed":
                break
        return "".join(chunks)

    @staticmethod
    def _extract_output_text(response) -> Optional[str]:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text.strip()

        pieces: List[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    pieces.append(text)
        if pieces:
            return "".join(pieces).strip()
        return None

    def _build_batch_payload(
        self,
        texts: List[str],
        original_indices: List[int],
        target_lang: str,
        source_lang: str,
        batch_context: Optional[str],
    ) -> Tuple[Dict[str, Any], List[Tuple[str, int]]]:
        target_name = self.LANG_NAMES.get(target_lang, target_lang)
        source_name = self.LANG_NAMES.get(source_lang, source_lang)

        total_chars = sum(len(text) for text in texts)
        char_budget = getattr(self, "batch_char_budget", self.MAX_BATCH_CHARS)
        if total_chars > char_budget:
            raise ValueError("Batch exceeds character budget for a single request")

        items: List[Dict[str, Any]] = []
        id_mapping: List[Tuple[str, int]] = []

        for local_id, (text, original_index) in enumerate(zip(texts, original_indices)):
            item_id = str(local_id)
            items.append({"id": item_id, "text": text})
            id_mapping.append((item_id, original_index))

        payload_obj = {"items": items}
        instructions = [
            f"Translate each item in the JSON array from {source_name} to {target_name}.",
            'Return a VALID JSON object with a key "translations" containing an array.',
            'Each element must be an object with keys "id" (string) and "translation" (string).',
            "Keep all whitespace, punctuation, and line breaks exactly as in the input text.",
            "Do not include explanations, markdown fences, or additional fields.",
        ]

        if batch_context:
            instructions.append(f"Batch context: {batch_context}")

        user_message = "\n".join(instructions) + "\n\nINPUT_JSON:\n" + json.dumps(payload_obj, ensure_ascii=False)

        messages = [
            {"role": "system", "content": self._build_system_prompt(target_lang, source_lang)},
            {"role": "user", "content": user_message},
        ]

        return {"messages": messages}, id_mapping

    def _parse_batch_response(self, content: Optional[str]) -> Optional[Dict[str, str]]:
        if not content:
            return None

        cleaned = self._strip_code_fence(content.strip())

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse batch response as JSON")
            return None

        translations = data.get("translations")
        if not isinstance(translations, list):
            logger.warning("Batch response missing 'translations' array")
            return None

        result: Dict[str, str] = {}
        for entry in translations:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get("id")
            translation = entry.get("translation")
            if entry_id is None or translation is None:
                continue
            result[str(entry_id)] = str(translation)

        return result or None

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        if not content.startswith("```"):
            return content

        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    @staticmethod
    def _messages_to_responses_input(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                converted.append(
                    {
                        "role": message.get("role", "user"),
                        "content": [{"type": "text", "text": content}],
                    }
                )
            else:
                converted.append(message)
        return converted
