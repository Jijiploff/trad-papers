"""
Factory y registro de traductores.
Proporciona una interfaz unificada para crear instancias de traductores
según el proveedor seleccionado.
"""
from typing import Dict, Type, Optional
from src.core.models import TranslationProvider
from src.translators.base import BaseTranslator
from src.translators.openai_translator import OpenAITranslator
from src.translators.deepl_translator import DeepLTranslator
from src.translators.gemini_translator import GeminiTranslator
from src.translators.fallback_translator import FallbackTranslator


class TranslatorFactory:
    """Fábrica para crear instancias de traductores."""

    @classmethod
    def create(
        cls,
        provider: TranslationProvider,
        config: dict,
        **kwargs,
    ) -> BaseTranslator:
        """
        Crea una instancia del traductor según el proveedor.

        Args:
            provider: Enumeración del proveedor
            config: Diccionario de configuración completo
            **kwargs: Parámetros adicionales que sobreescriben la config

        Returns:
            Instancia de BaseTranslator configurada
        """
        providers_config = config.get("providers", {})
        translation_config = config.get("translation", {})

        common_kwargs = {
            "max_retries": translation_config.get("max_retries", 3),
            "retry_delay": translation_config.get("retry_delay_seconds", 2.0),
            "timeout": translation_config.get("request_timeout_seconds", 120),
            "rate_limit_delay": translation_config.get("rate_limit_delay_seconds", 1.0),
        }
        common_kwargs.update(kwargs)

        if provider == TranslationProvider.OPENAI:
            openai_cfg = providers_config.get("openai", {})
            return OpenAITranslator(
                api_key=openai_cfg.get("api_key", ""),
                model=openai_cfg.get("model", "gpt-4o"),
                base_url=openai_cfg.get("base_url", "https://api.openai.com/v1"),
                temperature=openai_cfg.get("temperature", 0.3),
                **common_kwargs,
            )

        elif provider == TranslationProvider.DEEPL:
            deepl_cfg = providers_config.get("deepl", {})
            return DeepLTranslator(
                api_key=deepl_cfg.get("api_key", ""),
                base_url=deepl_cfg.get("base_url", "https://api.deepl.com/v2"),
                formality=deepl_cfg.get("formality", "default"),
                **common_kwargs,
            )

        elif provider == TranslationProvider.GEMINI:
            gemini_cfg = providers_config.get("gemini", {})
            return GeminiTranslator(
                api_key=gemini_cfg.get("api_key", ""),
                model=gemini_cfg.get("model", "gemini-1.5-flash"),
                temperature=gemini_cfg.get("temperature", 0.2),
                **common_kwargs,
            )

        elif provider == TranslationProvider.DEEPL:
            deepl_cfg = providers_config.get("deepl", {})
            return DeepLTranslator(
                api_key=deepl_cfg.get("api_key", ""),
                base_url=deepl_cfg.get("base_url", "https://api.deepl.com/v2"),
                formality=deepl_cfg.get("formality", "default"),
                **common_kwargs,
            )

        elif provider == TranslationProvider.OPENAI:
            openai_cfg = providers_config.get("openai", {})
            return OpenAITranslator(
                api_key=openai_cfg.get("api_key", ""),
                model=openai_cfg.get("model", "gpt-4o"),
                base_url=openai_cfg.get("base_url", "https://api.openai.com/v1"),
                temperature=openai_cfg.get("temperature", 0.3),
                **common_kwargs,
            )

        else:
            raise ValueError(f"Proveedor no soportado: {provider}")

    @classmethod
    def get_available_providers(cls, config: dict) -> Dict[TranslationProvider, bool]:
        """
        Verifica qué proveedores están disponibles y configurados.

        Returns:
            Diccionario {provider: está_disponible}
        """
        result = {}
        for provider in TranslationProvider:
            try:
                translator = cls.create(provider, config)
                result[provider] = translator.is_available()
            except Exception:
                result[provider] = False
        return result
