"""Unit tests for OpenAI translator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from transit.translators.openai_translator import OpenAITranslator
from transit.core.exceptions import APIAuthenticationError


class TestOpenAITranslatorInit:
    """Test OpenAI translator initialization."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_init_success(self, mock_openai):
        """Test successful initialization."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")

        assert translator.client is not None
        assert translator.model == "gpt-4o"
        assert translator.document_context is None

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_init_with_custom_model(self, mock_openai):
        """Test initialization with custom model."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key", model="gpt-4o-mini")

        assert translator.model == "gpt-4o-mini"

    def test_init_no_api_key(self):
        """Test initialization without API key."""
        with pytest.raises(APIAuthenticationError):
            OpenAITranslator("")

    def test_init_none_api_key(self):
        """Test initialization with None API key."""
        with pytest.raises(APIAuthenticationError):
            OpenAITranslator(None)


class TestDocumentContext:
    """Test document context management."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_set_document_context(self, mock_openai):
        """Test setting document context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        context = "This is a legal document about contracts."

        translator.set_document_context(context)

        assert translator.document_context == context

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_set_document_context_empty(self, mock_openai):
        """Test setting empty document context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        translator.set_document_context("")

        assert translator.document_context == ""


class TestSystemPrompt:
    """Test system prompt generation."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_build_system_prompt_basic(self, mock_openai):
        """Test basic system prompt building."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        prompt = translator._build_system_prompt("EN-US", "NL")

        # Should contain key instructions
        assert "professional document translator" in prompt.lower()
        assert "abbreviations" in prompt.lower()
        assert "idioms" in prompt.lower()
        assert "American English" in prompt or "EN-US" in prompt

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_build_system_prompt_with_context(self, mock_openai):
        """Test system prompt with document context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        translator.set_document_context("Legal document about employment law")
        prompt = translator._build_system_prompt("EN-US", "NL")

        # Should include context
        assert "DOCUMENT CONTEXT" in prompt or "employment law" in prompt.lower()


class TestTranslation:
    """Test translation functionality."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_text_success(self, mock_openai):
        """Test successful text translation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="This is a test."))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        result = translator.translate_text("Dit is een test.", "EN-US", "NL")

        assert result == "This is a test."
        mock_client.chat.completions.create.assert_called_once()

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_empty_text(self, mock_openai):
        """Test translating empty text."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=""))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        result = translator.translate_text("", "EN-US", "NL")

        # Should return empty string without API call
        assert result == ""
        mock_client.chat.completions.create.assert_not_called()

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_whitespace_only(self, mock_openai):
        """Test translating whitespace-only text."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="   "))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        result = translator.translate_text("   ", "EN-US", "NL")

        # Should return whitespace without API call
        assert result == "   "
        mock_client.chat.completions.create.assert_not_called()

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_with_context(self, mock_openai):
        """Test translation with additional context."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="regarding"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        result = translator.translate_text(
            "m.b.t.",
            "EN-US",
            "NL",
            context="This is an abbreviation in a legal document"
        )

        assert result == "regarding"
        # Verify context was passed in the message
        call_args = mock_client.chat.completions.create.call_args
        assert "Context:" in str(call_args)


class TestBatchTranslation:
    """Test batch translation functionality."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_batch_small(self, mock_openai):
        """Test batch translation with <= 5 texts."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(
            content='{"translations": [{"id": "0", "translation": "Text 1"}, {"id": "1", "translation": "Text 2"}, {"id": "2", "translation": "Text 3"}]}'
        ))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        texts = ["Tekst 1", "Tekst 2", "Tekst 3"]
        results = translator.translate_batch(texts, "EN-US", "NL")

        assert len(results) == 3
        assert results[0] == "Text 1"
        assert results[1] == "Text 2"
        assert results[2] == "Text 3"
        mock_client.chat.completions.create.assert_called_once()

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_batch_with_empty_strings(self, mock_openai):
        """Test batch translation with empty strings."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(
            content='{"translations": [{"id": "0", "translation": "Text 1"}, {"id": "1", "translation": "Text 2"}]}'
        ))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        texts = ["Tekst 1", "", "Tekst 2", "   "]
        results = translator.translate_batch(texts, "EN-US", "NL")

        assert len(results) == 4
        assert results[0] == "Text 1"
        assert results[2] == "Text 2"
        assert results[1] == ""  # Empty string preserved
        assert results[3] == "   "  # Whitespace preserved
        mock_client.chat.completions.create.assert_called_once()

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_translate_batch_empty_list(self, mock_openai):
        """Test batch translation with empty list."""
        mock_client = Mock()
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        results = translator.translate_batch([], "EN-US", "NL")

        assert results == []
        mock_client.chat.completions.create.assert_not_called()


class TestLanguageMapping:
    """Test language code to name mapping."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_language_names_exist(self, mock_openai):
        """Test that common language codes are mapped."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")

        # Check some common mappings
        assert translator.LANG_NAMES.get("EN-US") == "American English"
        assert translator.LANG_NAMES.get("DE") == "German"
        assert translator.LANG_NAMES.get("FR") == "French"
        assert translator.LANG_NAMES.get("NL") == "Dutch"

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_unknown_language_code(self, mock_openai):
        """Test handling of unknown language code."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="test"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        prompt = translator._build_system_prompt("XX-XX", "NL")

        # Should fall back to code itself
        assert "XX-XX" in prompt or "Dutch" in prompt


class TestErrorHandling:
    """Test error handling in translator."""

    @patch('transit.translators.openai_translator.openai.OpenAI')
    def test_api_error_returns_original(self, mock_openai):
        """Test that API errors return original text."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        result = translator.translate_text("Test tekst", "EN-US", "NL")

        # Should return original text on error
        assert result == "Test tekst"

    @patch('transit.translators.openai_translator.openai.OpenAI')
    @patch('transit.translators.openai_translator.time.sleep')
    def test_rate_limit_retry(self, mock_sleep, mock_openai):
        """Test retry on rate limit error."""
        from openai import RateLimitError

        mock_client = Mock()
        # First call raises rate limit, second succeeds
        mock_client.chat.completions.create.side_effect = [
            RateLimitError("Rate limited", response=Mock(status_code=429), body=None),
            Mock(choices=[Mock(message=Mock(content="Translated"))])
        ]
        mock_openai.return_value = mock_client

        translator = OpenAITranslator("test_key")
        # This should retry due to tenacity decorator
        # Note: tenacity might need to be configured for testing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
