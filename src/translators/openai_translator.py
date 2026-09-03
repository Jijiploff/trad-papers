"""
Traductor basado en OpenAI GPT-4o.
Usa la API oficial de OpenAI para traducciones de alta calidad.
"""
from typing import Optional

from src.translators.base import (
    BaseTranslator,
    TranslationError,
    TranslationAPIError,
    RateLimitError,
    AuthenticationError,
    TranslationTimeoutError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAITranslator(BaseTranslator):
    """Traductor usando la API de OpenAI (GPT-4o recomendado)."""

    # Costos aproximados (Q3 2026) - actualizar según precios vigentes
    # GPT-4o: $5.00 / 1M tokens de entrada, $15.00 / 1M tokens de salida
    COST_PER_1M_INPUT = 5.00
    COST_PER_1M_OUTPUT = 15.00

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        """Inicializa el cliente de OpenAI de forma lazy."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except ImportError:
                raise TranslationError(
                    "El paquete 'openai' no está instalado. "
                    "Instálalo con: pip install openai>=1.0.0"
                )
        return self._client

    def get_provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self.api_key) and len(self.api_key) > 10

    def translate_text(self, text: str, source_lang: str = "EN", target_lang: str = "ES") -> str:
        """Traduce un texto usando la API de Chat Completions de OpenAI."""
        if not self.is_available():
            raise AuthenticationError("API key de OpenAI no configurada o inválida")

        try:
            client = self._get_client()

            user_prompt = (
                f"Traduce el siguiente texto académico del inglés al español.\n"
                f"Instrucciones importantes:\n"
                f"- Mantén la terminología técnica precisa\n"
                f"- NO traduzcas contenido matemático entre $, $$, \\(, \\), \\begin{{equation}}, etc.\n"
                f"- NO traduzcas citas como [1], (Author, 2020), \\cite{{...}}\n"
                f"- NO traduzcas referencias como \\ref{{...}}, \\label{{...}}\n"
                f"- Mantén la estructura de párrafos\n\n"
                f"Texto a traducir:\n{text}"
            )

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )

            translated = response.choices[0].message.content

            if not translated:
                raise TranslationAPIError("La API devolvió una respuesta vacía")

            return translated.strip()

        except AuthenticationError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                raise RateLimitError(f"Rate limit OpenAI: {e}")
            elif "timeout" in error_str or "timed out" in error_str:
                raise TranslationTimeoutError(f"Timeout OpenAI: {e}")
            elif "authentication" in error_str or "401" in error_str or "invalid_api_key" in error_str:
                raise AuthenticationError(f"Autenticación OpenAI fallida: {e}")
            else:
                raise TranslationAPIError(f"Error OpenAI API: {e}")

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> dict:
        """Estima el costo usando las tarifas de GPT-4o."""
        output = output_tokens or input_tokens  # Asumir ~misma longitud
        cost_input = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT
        cost_output = (output / 1_000_000) * self.COST_PER_1M_OUTPUT
        total = cost_input + cost_output

        return {
            "provider": f"openai ({self.model})",
            "input_tokens": input_tokens,
            "output_tokens": output,
            "total_tokens": input_tokens + output,
            "cost_input_usd": round(cost_input, 6),
            "cost_output_usd": round(cost_output, 6),
            "estimated_cost_usd": round(total, 6),
            "currency": "USD",
            "notes": "Precios aproximados Q3 2026. Verificar en openai.com/pricing",
        }
