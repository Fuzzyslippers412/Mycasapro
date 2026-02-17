"""
LLM Client for MyCasa Pro Agents.
Supports multiple providers: Anthropic Claude, Google Gemini, OpenAI-compatible APIs.
"""
import os
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Try to import SDKs
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic SDK not installed")

try:
    from openai import OpenAI
    import httpx
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai SDK not installed")

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("google-generativeai SDK not installed")


class LLMClient:
    """
    Centralized LLM client for all agents.
    Supports multiple providers via configuration.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_type: Optional[str] = None
    ):
        """
        Initialize LLM client.

        Args:
            api_key: API key (or uses LLM_API_KEY env var)
            model: Model ID to use (or uses LLM_MODEL env var)
            provider: Provider type: "anthropic", "openai", or "openai-compatible" (or uses LLM_PROVIDER env var)
            base_url: Base URL for OpenAI-compatible APIs (or uses LLM_BASE_URL env var)
        """
        self.provider = provider or self._default_provider()
        self.base_url = self._resolve_base_url(base_url)
        self.auth_type = auth_type
        if self.auth_type == "qwen-oauth":
            self.api_key = api_key
        else:
            self.api_key = api_key or self._resolve_api_key()
        self.model = model or self._resolve_model()
        self.client = None
        self._allow_no_api_key = bool(
            os.getenv("LLM_ALLOW_NO_API_KEY", "").lower() == "true"
        )

        # Initialize client based on provider
        if self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "google":
            self._init_google()
        elif self.provider in ["openai", "openai-compatible"]:
            self._init_openai()
        else:
            logger.error(f"Unknown provider: {self.provider}")

    def _init_anthropic(self):
        """Initialize Anthropic Claude client"""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic SDK not available - install with: pip install anthropic")
            return

        if not self.api_key:
            logger.warning("No API key found - agent chat will use fallback responses")
            return

        try:
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"Anthropic client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")

    def _init_google(self):
        """Initialize Google Gemini client"""
        if not GOOGLE_AVAILABLE:
            logger.error("Google SDK not available - install with: pip install google-generativeai")
            return

        if not self.api_key:
            logger.warning("No API key found - agent chat will use fallback responses")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"Google Gemini client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Google client: {e}")

    def _init_openai(self):
        """Initialize OpenAI-compatible client (Venice AI, Qwen, etc.)"""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI SDK not available - install with: pip install openai")
            return

        if not self.api_key:
            if self._allow_no_api_key or self._is_local_base_url(self.base_url):
                self.api_key = "local"
            else:
                logger.warning("No API key found - agent chat will use fallback responses")
                return

        try:
            # Use sync client - we'll wrap calls in asyncio.to_thread for async
            # Longer timeout for slower providers like Venice AI
            kwargs = {
                "api_key": self.api_key,
                "timeout": 120.0,
                "max_retries": 2,
                "http_client": httpx.Client(timeout=120.0)
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            if self.auth_type == "qwen-oauth":
                kwargs["default_headers"] = {
                    "X-DashScope-AuthType": "qwen-oauth",
                }

            self.client = OpenAI(**kwargs)
            logger.info(f"OpenAI-compatible client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    def _default_provider(self) -> str:
        provider = os.getenv("LLM_PROVIDER")
        if provider:
            return provider

        if os.getenv("LLM_AUTH_TYPE") == "qwen-oauth":
            return "openai-compatible"

        # If explicit OpenAI base URL or local host is provided, use OpenAI-compatible.
        if (
            os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or os.getenv("OLLAMA_HOST")
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("LMSTUDIO_BASE_URL")
            or os.getenv("LOCAL_LLM_BASE_URL")
        ):
            return "openai-compatible"

        if os.getenv("OPENAI_API_KEY"):
            return "openai"

        if os.getenv("LLM_API_KEY"):
            return "openai"

        if os.getenv("VENICE_API_KEY") or os.getenv("QWEN_API_KEY"):
            return "openai-compatible"

        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"

        # Default to local OpenAI-compatible for Qwen.
        return "openai-compatible"

    def _resolve_base_url(self, base_url: Optional[str]) -> Optional[str]:
        if base_url:
            return self._normalize_base_url(base_url)

        env_base = (
            os.getenv("LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or os.getenv("LMSTUDIO_BASE_URL")
            or os.getenv("LOCAL_LLM_BASE_URL")
        )
        if env_base:
            return self._normalize_base_url(env_base)

        ollama_host = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL")
        if ollama_host:
            return self._normalize_base_url(ollama_host)

        if self.provider in ["openai", "anthropic"]:
            return None

        # Default to local Ollama if nothing else is provided.
        return "http://localhost:11434/v1"

    def _resolve_api_key(self) -> Optional[str]:
        # User-provided API key for OpenAI-compatible or Anthropic.
        return (
            os.getenv("LLM_API_KEY")
            or os.getenv("VENICE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )

    def _resolve_model(self) -> str:
        explicit = os.getenv("LLM_MODEL")
        if explicit:
            return explicit

        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet"

        if self.provider == "openai":
            return os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

        return (
            os.getenv("QWEN_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or "qwen2.5:7b"
        )

    def _normalize_base_url(self, raw_url: str) -> str:
        url = raw_url.strip()
        if not url:
            return url
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        if url.endswith("/v1"):
            return url
        if url.endswith("/v1/"):
            return url[:-1]
        return f"{url.rstrip('/')}/v1"

    def _is_local_base_url(self, base_url: Optional[str]) -> bool:
        if not base_url:
            return False
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "0.0.0.0"}

    def is_available(self) -> bool:
        """Check if LLM client is ready to use"""
        return self.client is not None

    def _is_auth_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        if "401" in message or "unauthorized" in message or "authentication failed" in message:
            return True
        status_code = getattr(exc, "status_code", None)
        if status_code in {401, 403}:
            return True
        response = getattr(exc, "response", None)
        if response is not None:
            resp_code = getattr(response, "status_code", None)
            if resp_code in {401, 403}:
                return True
        return False

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0
    ) -> str:
        """
        Send a chat message and get response.

        Args:
            system_prompt: System prompt defining agent persona and role
            user_message: User's message to respond to
            conversation_history: Previous messages in format [{"role": "user", "content": "..."}, ...]
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            Agent's response text
        """
        if not self.is_available():
            return f"[LLM unavailable] Default response to: {user_message[:50]}..."

        try:
            if self.auth_type == "qwen-oauth":
                await self._ensure_qwen_oauth()
            if self.provider == "anthropic":
                return await self._chat_anthropic(system_prompt, user_message, conversation_history, max_tokens, temperature)
            elif self.provider == "google":
                return await self._chat_google(system_prompt, user_message, conversation_history, max_tokens, temperature)
            elif self.provider in ["openai", "openai-compatible"]:
                return await self._chat_openai(system_prompt, user_message, conversation_history, max_tokens, temperature)
            else:
                return f"[Unknown provider: {self.provider}]"

        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            if self.auth_type == "qwen-oauth" and self._is_auth_error(e):
                return "[Qwen OAuth required] Authentication failed. Reconnect in Settings or run: ./mycasa llm qwen-login"
            return f"[Error calling LLM: {str(e)}]"

    async def chat_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chat using OpenAI-style messages and return usage when available."""
        if self.auth_type == "qwen-oauth":
            await self._ensure_qwen_oauth()
        if not self.is_available():
            return {
                "response": "[LLM unavailable] Default response.",
                "usage": None,
                "model_used": model or self.model,
                "provider": self.provider,
            }

        use_model = model or self.model

        try:
            if self.provider == "anthropic":
                system_parts = [m["content"] for m in messages if m.get("role") == "system"]
                system_prompt = "\n\n".join([p for p in system_parts if p])
                anthropic_messages = [
                    {"role": m.get("role"), "content": m.get("content", "")}
                    for m in messages
                    if m.get("role") in {"user", "assistant"}
                ]
                response = self.client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=anthropic_messages,
                )
                text = response.content[0].text if response.content else ""
                usage = None
                if hasattr(response, "usage") and response.usage:
                    usage = {
                        "input_tokens": getattr(response.usage, "input_tokens", None),
                        "output_tokens": getattr(response.usage, "output_tokens", None),
                    }
                return {
                    "response": text,
                    "usage": usage,
                    "model_used": use_model,
                    "provider": self.provider,
                }

            if self.provider == "google":
                # Gemini expects a single prompt string; serialize messages deterministically.
                system_parts = [m["content"] for m in messages if m.get("role") == "system"]
                prompt_lines = []
                if system_parts:
                    prompt_lines.append("System:")
                    prompt_lines.append("\n\n".join(system_parts))
                for msg in messages:
                    if msg.get("role") == "system":
                        continue
                    role = msg.get("role", "user")
                    prompt_lines.append(f"{role.capitalize()}: {msg.get('content', '')}")
                prompt = "\n\n".join(prompt_lines).strip()

                def _sync_call():
                    return self.client.generate_content(
                        prompt,
                        generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
                    )

                import asyncio
                response = await asyncio.to_thread(_sync_call)
                text = getattr(response, "text", "") or ""
                usage = None
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = {
                        "input_tokens": response.usage_metadata.get("prompt_token_count"),
                        "output_tokens": response.usage_metadata.get("candidates_token_count"),
                    }
                return {
                    "response": text,
                    "usage": usage,
                    "model_used": use_model,
                    "provider": self.provider,
                }

            if self.provider in ["openai", "openai-compatible"]:
                import asyncio

                def _sync_call():
                    return self.client.chat.completions.create(
                        model=use_model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        messages=messages,
                    )
                try:
                    response = await asyncio.to_thread(_sync_call)
                except Exception as e:
                    if self.auth_type == "qwen-oauth" and self._is_auth_error(e):
                        await self._ensure_qwen_oauth()
                        response = await asyncio.to_thread(_sync_call)
                    else:
                        raise
                text = response.choices[0].message.content if response.choices else ""
                usage = None
                if hasattr(response, "usage") and response.usage:
                    usage = {
                        "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
                        "completion_tokens": getattr(response.usage, "completion_tokens", None),
                        "input_tokens": getattr(response.usage, "prompt_tokens", None),
                        "output_tokens": getattr(response.usage, "completion_tokens", None),
                    }
                return {
                    "response": text,
                    "usage": usage,
                    "model_used": use_model,
                    "provider": self.provider,
                }

            return {
                "response": f"[Unknown provider: {self.provider}]",
                "usage": None,
                "model_used": use_model,
                "provider": self.provider,
            }
        except Exception as e:
            logger.error(f"LLM chat_messages error: {e}")
            if self.auth_type == "qwen-oauth" and self._is_auth_error(e):
                return {
                    "response": "[Qwen OAuth required] Authentication failed. Reconnect in Settings or run: ./mycasa llm qwen-login",
                    "usage": None,
                    "model_used": use_model,
                    "provider": self.provider,
                }
            return {
                "response": f"[Error calling LLM: {str(e)}]",
                "usage": None,
                "model_used": use_model,
                "provider": self.provider,
            }

    async def chat_messages_routed(
        self,
        agent_id: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 1.0,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chat with automatic routing using OpenAI-style messages."""
        from core.request_scorer import get_request_scorer

        # Score based on last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        scorer = get_request_scorer()
        scoring = scorer.score(user_message or "", agent_id)

        original_model = self.model
        if force_model:
            model = force_model
        elif self.provider == "anthropic":
            model = scoring.recommended_model
        else:
            model = self.model

        if model:
            self.model = model

        try:
            result = await self.chat_messages(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
        finally:
            self.model = original_model

        return {
            "response": result.get("response"),
            "usage": result.get("usage"),
            "model_used": model,
            "provider": self.provider,
            "routing": {
                "score": scoring.score,
                "tier": scoring.tier.value,
                "confidence": scoring.confidence,
                "factors": scoring.factors,
                "recommended_model": scoring.recommended_model,
            },
            "agent_id": agent_id,
        }

    async def _ensure_qwen_oauth(self) -> None:
        try:
            from core.settings_typed import get_settings_store
            from core.qwen_oauth import is_token_expired, refresh_access_token, build_oauth_settings

            store = get_settings_store()
            settings = store.get()
            oauth = getattr(settings.system, "llm_oauth", None) or {}
            if not oauth or not oauth.get("refresh_token"):
                return
            if not is_token_expired(oauth):
                return
            refreshed = await refresh_access_token(oauth["refresh_token"])
            settings.system.llm_oauth = build_oauth_settings(refreshed)
            settings.system.llm_auth_type = "qwen-oauth"
            settings.system.llm_provider = "openai-compatible"
            settings.system.llm_base_url = settings.system.llm_oauth.get("resource_url")
            settings.system.llm_api_key = None
            store.save(settings)

            # Update the in-memory client
            self.api_key = settings.system.llm_oauth.get("access_token")
            self.base_url = settings.system.llm_oauth.get("resource_url")
            if self.provider in ["openai", "openai-compatible"]:
                self._init_openai()
        except Exception:
            return

    def chat_sync(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
    ) -> str:
        """Synchronous chat helper for sync code paths."""
        if not self.is_available():
            return f"[LLM unavailable] Default response to: {user_message[:50]}..."

        try:
            if self.auth_type == "qwen-oauth":
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(self._ensure_qwen_oauth())
                else:
                    loop.create_task(self._ensure_qwen_oauth())
            if self.provider == "anthropic":
                messages = []
                if conversation_history:
                    messages.extend(conversation_history)
                messages.append({"role": "user", "content": user_message})

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                )
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                logger.warning("Empty response from Claude API")
                return "I apologize, but I'm having trouble formulating a response right now."

            if self.provider in ["openai", "openai-compatible"]:
                messages = [{"role": "system", "content": system_prompt}]
                if conversation_history:
                    messages.extend(conversation_history)
                messages.append({"role": "user", "content": user_message})

                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                )
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content
                logger.warning("Empty response from OpenAI-compatible API")
                return "I apologize, but I'm having trouble formulating a response right now."

            return f"[Unknown provider: {self.provider}]"
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            if self.auth_type == "qwen-oauth" and self._is_auth_error(e):
                return "[Qwen OAuth required] Authentication failed. Reconnect in Settings or run: ./mycasa llm qwen-login"
            return f"[Error calling LLM: {str(e)}]"

    async def _chat_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call Anthropic Claude API"""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages
        )

        if response.content and len(response.content) > 0:
            return response.content[0].text
        else:
            logger.warning("Empty response from Claude API")
            return "I apologize, but I'm having trouble formulating a response right now."

    async def _chat_google(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call Google Gemini API"""
        import asyncio

        # Build conversation for Gemini
        # Gemini uses a different format: alternating user/model messages
        contents = []

        # Add system prompt as first user message (Gemini doesn't have system role)
        full_prompt = f"{system_prompt}\n\n---\n\n"

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})

        # Add current message
        if contents:
            contents.append({"role": "user", "parts": [user_message]})
        else:
            # First message includes system prompt
            contents.append({"role": "user", "parts": [full_prompt + user_message]})

        # Run sync call in thread pool
        def _sync_call():
            response = self.client.generate_content(
                contents,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            return response

        response = await asyncio.to_thread(_sync_call)

        if response.text:
            return response.text
        else:
            logger.warning("Empty response from Gemini API")
            return "I apologize, but I'm having trouble formulating a response right now."

    async def _chat_openai(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Call OpenAI-compatible API (Venice AI, Qwen, etc.)"""
        import asyncio

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        # Run sync client in thread pool to avoid anyio detection issues
        def _sync_call():
            return self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )

        response = await asyncio.to_thread(_sync_call)

        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            logger.warning("Empty response from OpenAI-compatible API")
            return "I apologize, but I'm having trouble formulating a response right now."


    async def chat_routed(
        self,
        agent_id: str,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Chat with automatic model routing based on request complexity.

        Uses the RequestScorer to analyze the request and route to the
        cheapest capable model (Haiku → Sonnet → Opus).

        Args:
            agent_id: The agent making the request (affects tier adjustment)
            system_prompt: System prompt
            user_message: User's message
            conversation_history: Previous messages
            max_tokens: Max response tokens
            temperature: Sampling temperature
            force_model: Override automatic routing with specific model

        Returns:
            Dict with 'response', 'model_used', and 'routing' metadata
        """
        from core.request_scorer import get_request_scorer, ModelTier

        # Score the request
        scorer = get_request_scorer()
        scoring = scorer.score(user_message, agent_id)

        # Determine model to use
        # For Anthropic, use the scorer's recommended model
        # For other providers (Venice, OpenAI-compatible), use the configured model
        original_model = self.model

        if force_model:
            model = force_model
            self.model = force_model
        elif self.provider == "anthropic":
            model = scoring.recommended_model
            self.model = model
        else:
            # Non-Anthropic providers: use configured model, routing is informational only
            model = self.model

        try:
            # Make the call
            response = await self.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        finally:
            # Restore original model
            self.model = original_model

        return {
            "response": response,
            "model_used": model,
            "routing": {
                "score": scoring.score,
                "tier": scoring.tier.value,
                "confidence": scoring.confidence,
                "factors": scoring.factors,
                "recommended_model": scoring.recommended_model,
            },
            "agent_id": agent_id,
        }

    def chat_routed_sync(
        self,
        agent_id: str,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 2048,
        temperature: float = 1.0,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous version of chat_routed."""
        from core.request_scorer import get_request_scorer

        # Score the request
        scorer = get_request_scorer()
        scoring = scorer.score(user_message, agent_id)

        # Determine model
        model = force_model or scoring.recommended_model

        # For Anthropic, handle model selection
        original_model = self.model
        if self.provider == "anthropic":
            self.model = model

        try:
            response = self.chat_sync(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        finally:
            self.model = original_model

        return {
            "response": response,
            "model_used": model,
            "routing": {
                "score": scoring.score,
                "tier": scoring.tier.value,
                "confidence": scoring.confidence,
                "factors": scoring.factors,
                "recommended_model": scoring.recommended_model,
            },
            "agent_id": agent_id,
        }


# Global instance
_llm_client: Optional[LLMClient] = None


def reset_llm_client() -> None:
    """Reset the global LLM client so new settings take effect."""
    global _llm_client
    _llm_client = None


def _resolve_settings_llm_config() -> dict:
    config: dict[str, Optional[str]] = {}
    try:
        from core.settings_typed import get_settings_store

        settings = get_settings_store().get()
        system = settings.system
        auth_type = getattr(system, "llm_auth_type", None)
        if auth_type == "qwen-oauth":
            oauth = getattr(system, "llm_oauth", None) or {}
            config["auth_type"] = "qwen-oauth"
            config["provider"] = "openai-compatible"
            if oauth.get("resource_url"):
                config["base_url"] = oauth.get("resource_url")
            if oauth.get("access_token"):
                config["api_key"] = oauth.get("access_token")
        if auth_type != "qwen-oauth":
            if getattr(system, "llm_provider", None):
                config["provider"] = system.llm_provider
            if getattr(system, "llm_base_url", None):
                config["base_url"] = system.llm_base_url
            if getattr(system, "llm_model", None):
                config["model"] = system.llm_model
            if getattr(system, "llm_api_key", None):
                config["api_key"] = system.llm_api_key
        else:
            if getattr(system, "llm_model", None):
                config["model"] = system.llm_model
    except Exception:
        pass
    return config


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        settings_config = _resolve_settings_llm_config()
        auth_type = settings_config.get("auth_type")
        if auth_type == "qwen-oauth":
            try:
                from core.settings_typed import get_settings_store
                from core.qwen_oauth import is_token_expired, refresh_access_token_sync, build_oauth_settings

                store = get_settings_store()
                settings = store.get()
                oauth = getattr(settings.system, "llm_oauth", None) or {}
                if is_token_expired(oauth) and oauth.get("refresh_token"):
                    refreshed = refresh_access_token_sync(oauth["refresh_token"])
                    settings.system.llm_oauth = build_oauth_settings(refreshed)
                    settings.system.llm_auth_type = "qwen-oauth"
                    settings.system.llm_provider = "openai-compatible"
                    settings.system.llm_base_url = settings.system.llm_oauth.get("resource_url")
                    settings.system.llm_api_key = None
                    store.save(settings)
                    settings_config = _resolve_settings_llm_config()
                    auth_type = settings_config.get("auth_type")
            except Exception:
                pass
        if auth_type == "qwen-oauth":
            provider = settings_config.get("provider") or "openai-compatible"
            base_url = settings_config.get("base_url")
            model = settings_config.get("model")
            api_key = settings_config.get("api_key")
        else:
            provider = os.getenv("LLM_PROVIDER") or settings_config.get("provider")
            base_url = os.getenv("LLM_BASE_URL") or settings_config.get("base_url")
            model = os.getenv("LLM_MODEL") or settings_config.get("model")
            api_key = os.getenv("LLM_API_KEY") or settings_config.get("api_key")
        _llm_client = LLMClient(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            auth_type=auth_type,
        )
    return _llm_client
