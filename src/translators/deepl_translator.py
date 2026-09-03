"""
Traductor basado en DeepL API.
DeepL ofrece alta calidad en traducciones generales y académicas.
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


class DeepLTranslator(BaseTranslator):
    """Traductor usando la API oficial de DeepL."""

    # Costos aproximados (Q3 2026)
    # DeepL API Free: 500,000 caracteres/mes gratis
    # DeepL API Pro: $4.99/mes + $0.00002/character (=$20/1M caracteres ≈ $5/1M tokens)
    COST_PER_CHAR = 0.00002  # USD por carácter (plan Pro)
    MONTHLY_FEE = 4.99

    # Mapeo de códigos de idioma para DeepL
    LANG_MAP = {
        "EN": "EN",
        "ES": "ES",
        "PT": "PT-PT",
        "FR": "FR",
        "DE": "DE",
        "IT": "IT",
        "JA": "JA",
        "ZH": "ZH",
    }

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepl.com/v2",
        formality: str = "default",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.formality = formality
        self._client = None

        # Detectar si es cuenta gratuita (cambia la URL)
        if ':fx' in api_key and 'api-free.deepl.com' not in base_url:
            self.base_url = "https://api-free.deepl.com/v2"

    def _get_client(self):
        """Inicializa el cliente de DeepL de forma lazy."""
        if self._client is None:
            try:
                import deepl
                self._client = deepl.Translator(self.api_key, server_url=self.base_url)
            except ImportError:
                raise TranslationError(
                    "El paquete 'deepl' no está instalado. "
                    "Instálalo con: pip install deepl"
                )
        return self._client

    def get_provider_name(self) -> str:
        return "deepl"

    def is_available(self) -> bool:
        return bool(self.api_key) and len(self.api_key) > 5

    def translate_text(self, text: str, source_lang: str = "EN", target_lang: str = "ES") -> str:
        if not self.is_available():
            raise AuthenticationError("API key de DeepL no configurada")

        try:
            client = self._get_client()

            source = self.LANG_MAP.get(source_lang, source_lang)
            target = self.LANG_MAP.get(target_lang, target_lang)

            # ESCAPAR caracteres especiales para XML
            import html
            escaped_text = html.escape(text)
            
            # Usar tag_handling con XML correctamente escapado
            result = client.translate_text(
                escaped_text,
                source_lang=source,
                target_lang=target,
                formality=self.formality,
                preserve_formatting=True,
                tag_handling="xml",
                # IMPORTANTE: No usar ignore_tags con textos largos, mejor usar split_sentences
                split_sentences='nonewlines',  # Alternativa para preservar formato
            )

            translated = result.text if hasattr(result, 'text') else str(result)

            if not translated:
                raise TranslationAPIError("DeepL devolvió una respuesta vacía")

            # Decodificar la salida
            import html
            return html.unescape(translated.strip())

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "too many requests" in error_str or "quota" in error_str:
                raise RateLimitError(f"Rate limit o cuota DeepL excedida: {e}")
            elif "401" in error_str or "403" in error_str or "unauthorized" in error_str:
                raise AuthenticationError(f"Autenticación DeepL fallida: {e}")
            elif "timeout" in error_str or "timed out" in error_str:
                raise TranslationTimeoutError(f"Timeout DeepL: {e}")
            else:
                raise TranslationAPIError(f"Error DeepL API: {e}")

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> dict:
        """
        Estima el costo de DeepL.
        Nota: DeepL cobra por caracteres, no por tokens.
        Aproximación: 1 token ≈ 4 caracteres.
        """
        input_chars = input_tokens * 4
        output_chars = (output_tokens or input_tokens) * 4
        total_chars = input_chars + output_chars

        cost_pro = total_chars * self.COST_PER_CHAR

        return {
            "provider": "deepl",
            "input_tokens": input_tokens,
            "input_chars_approx": input_chars,
            "output_chars_approx": output_chars,
            "total_chars_approx": total_chars,
            "estimated_cost_pro_usd": round(cost_pro, 6),
            "monthly_fee_pro_usd": self.MONTHLY_FEE,
            "free_tier_limit_chars": 500000,
            "currency": "USD",
            "notes": (
                "Plan Free: 500K caracteres/mes gratis. "
                "Plan Pro: $4.99/mes + $0.00002/caracter. "
                "Precios aproximados Q3 2026. Verificar en deepl.com/pro-api"
            ),
        }
