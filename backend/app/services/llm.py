"""LLM provider abstraction supporting OpenAI, Anthropic, and Google Gemini."""

from __future__ import annotations

from typing import AsyncIterator

from app.config import settings


class LLMProvider:
    """Thin async wrapper around LLM streaming APIs.

    Selected via the ``LLM_PROVIDER`` env var ("openai" | "anthropic" | "gemini").
    """

    def __init__(self, provider: str | None = None, model: str | None = None) -> None:
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        system: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Yield text tokens streamed from the configured LLM.

        Args:
            system:   System-prompt string.
            messages: Conversation turns – ``[{"role": "user"|"assistant",
                      "content": "..."}]``.

        Yields:
            Individual text tokens / chunks as plain strings.
        """
        if self.provider == "openai":
            async for token in self._stream_openai(system, messages):
                yield token
        elif self.provider == "anthropic":
            async for token in self._stream_anthropic(system, messages):
                yield token
        elif self.provider == "gemini":
            async for token in self._stream_gemini(system, messages):
                yield token
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider!r}")

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    async def _stream_openai(
        self,
        system: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI  # lazy import

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        openai_messages = [{"role": "system", "content": system}] + messages

        stream = await client.chat.completions.create(
            model=self.model,
            messages=openai_messages,  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _stream_anthropic(
        self,
        system: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        import anthropic  # lazy import

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        async with client.messages.stream(
            model=self.model,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=4096,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_gemini(
        self,
        system: str,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        import asyncio
        import google.generativeai as genai  # lazy import

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
        )

        # Convert messages to Gemini's Content format
        gemini_history: list[dict] = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        last_user_content = messages[-1]["content"] if messages else ""

        chat = model.start_chat(history=gemini_history)  # type: ignore[arg-type]

        # Gemini's streaming is sync; run in executor to stay async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: chat.send_message(last_user_content, stream=True),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
