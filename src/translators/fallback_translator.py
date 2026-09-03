"""
Traductor con fallback automático.
Intenta traducir con el proveedor primario (Gemini) y si falla por:
- Límite de cuota / rate limit alcanzado
- Timeout
- Error de API no recuperable
- Proveedor no disponible

Automáticamente cambia al proveedor secundario (DeepL) sin intervención del usuario.
"""
from typing import List, Optional, Callable

from src.translators.base import (
    BaseTranslator,
    TranslationError,
    RateLimitError,
    TranslationTimeoutError,
    TranslationAPIError,
    AuthenticationError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackTranslator(BaseTranslator):
    """
    Traductor que envuelve múltiples proveedores en orden de prioridad.
    Si el primario falla, prueba automáticamente con el siguiente.

    Orden por defecto: Gemini (primario, gratis) -> DeepL (secundario, free tier)
    """

    def __init__(
        self,
        translators: List[BaseTranslator],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.translators = translators
        self._active_index = 0
        self._fallback_triggered = False
        self._last_fallback_reason = ""

    @classmethod
    def create_default(cls, config: dict, **kwargs) -> 'FallbackTranslator':
        """
        Crea un FallbackTranslator con el orden estándar: Gemini -> DeepL.

        Args:
            config: Diccionario de configuración completo
            **kwargs: Parámetros comunes para todos los traductores

        Returns:
            FallbackTranslator configurado con Gemini + DeepL
        """
        from src.translators import TranslatorFactory
        from src.core.models import TranslationProvider

        translators = []

        # 1. Gemini (primario - gratuito)
        try:
            gemini = TranslatorFactory.create(TranslationProvider.GEMINI, config, **kwargs)
            if gemini.is_available():
                translators.append(gemini)
                logger.info("Fallback: Gemini configurado como proveedor primario")
            else:
                logger.warning("Fallback: Gemini no disponible, se omitirá")
        except Exception as e:
            logger.warning(f"Fallback: No se pudo inicializar Gemini: {e}")

        # 2. DeepL (secundario - free tier)
        try:
            deepl = TranslatorFactory.create(TranslationProvider.DEEPL, config, **kwargs)
            if deepl.is_available():
                translators.append(deepl)
                logger.info("Fallback: DeepL configurado como proveedor secundario")
            else:
                logger.warning("Fallback: DeepL no disponible, se omitirá")
        except Exception as e:
            logger.warning(f"Fallback: No se pudo inicializar DeepL: {e}")

        # 3. OpenAI como último recurso si está configurado
        try:
            openai = TranslatorFactory.create(TranslationProvider.OPENAI, config, **kwargs)
            if openai.is_available():
                translators.append(openai)
                logger.info("Fallback: OpenAI configurado como proveedor terciario")
        except Exception as e:
            logger.debug(f"Fallback: OpenAI no disponible: {e}")

        if not translators:
            raise TranslationError(
                "Ningún proveedor de traducción está disponible. "
                "Configura al menos Gemini o DeepL en config.yaml."
            )

        return cls(translators, **kwargs)

    def get_provider_name(self) -> str:
        """Devuelve el nombre del proveedor actualmente activo."""
        active = self.translators[self._active_index]
        return f"fallback->{active.get_provider_name()}"

    def get_active_provider(self) -> BaseTranslator:
        """Devuelve la instancia del traductor actualmente activo."""
        return self.translators[self._active_index]

    def is_available(self) -> bool:
        """Al menos un proveedor debe estar disponible."""
        return any(t.is_available() for t in self.translators)

    def _should_fallback(self, error: Exception) -> bool:
        """
        Determina si un error justifica hacer fallback al siguiente proveedor.
        Hacemos fallback para errores recuperables / de cuota.
        NO hacemos fallback para errores de autenticación (probablemente todas las keys fallarán).
        """
        if isinstance(error, AuthenticationError):
            return False  # No hacer fallback si es problema de credenciales
        if isinstance(error, RateLimitError):
            return True   # Cuota agotada -> cambiar de proveedor
        if isinstance(error, TranslationTimeoutError):
            return True   # Timeout -> probar otro
        if isinstance(error, TranslationAPIError):
            error_str = str(error).lower()
            # Hacer fallback para errores de servidor o cuota
            if any(kw in error_str for kw in ['quota', 'exhausted', 'limit', 'server', '500', '503', 'unavailable', 'overloaded']):
                return True
            return False
        if isinstance(error, TranslationError):
            return True
        return False

    def translate_text(self, text: str, source_lang: str = "EN", target_lang: str = "ES") -> str:
        """
        Intenta traducir con el proveedor activo. Si falla y corresponde,
        hace fallback automáticamente al siguiente proveedor.
        """
        last_error = None

        for idx in range(self._active_index, len(self.translators)):
            translator = self.translators[idx]
            provider_name = translator.get_provider_name()

            try:
                if idx > self._active_index:
                    logger.info(
                        f"Fallback activado: cambiando de "
                        f"{self.translators[self._active_index].get_provider_name()} "
                        f"a {provider_name}. Motivo: {self._last_fallback_reason}"
                    )
                    self._active_index = idx
                    self._fallback_triggered = True

                logger.debug(f"Intentando traducción con: {provider_name}")
                result = translator.translate_text(text, source_lang, target_lang)
                return result

            except Exception as e:
                last_error = e
                if self._should_fallback(e) and idx < len(self.translators) - 1:
                    self._last_fallback_reason = str(e)
                    logger.warning(
                        f"Proveedor {provider_name} falló ({type(e).__name__}: {e}). "
                        f"Intentando fallback..."
                    )
                    continue
                else:
                    # No hacer fallback o no hay más proveedores
                    logger.error(
                        f"Proveedor {provider_name} falló sin posibilidad de fallback: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise

        # Si llegamos aquí, todos los proveedores fallaron
        raise TranslationError(
            f"Todos los proveedores de traducción fallaron. "
            f"Último error: {type(last_error).__name__}: {last_error}"
        )

    def translate_with_retry(
        self,
        text: str,
        source_lang: str = "EN",
        target_lang: str = "ES",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Versión con reintentos que también maneja fallback.
        Primero agota los reintentos en el proveedor actual, luego hace fallback.
        """
        if not text or not text.strip():
            return text

        attempt = 0
        last_exception = None
        current_provider_index = self._active_index

        while attempt <= self.max_retries:
            try:
                self._enforce_rate_limit()

                # Si cambiamos de proveedor por fallback, reiniciar intentos
                if self._active_index != current_provider_index:
                    current_provider_index = self._active_index
                    attempt = 0

                result = self.translate_text(text, source_lang, target_lang)

                if progress_callback:
                    progress_callback(1.0)

                return result

            except RateLimitError as e:
                # Rate limit -> hacer fallback INMEDIATO sin reintentar en el mismo proveedor
                if self._active_index < len(self.translators) - 1:
                    self._last_fallback_reason = str(e)
                    self._active_index += 1
                    self._fallback_triggered = True
                    logger.warning(
                        f"Rate limit alcanzado en proveedor actual. "
                        f"Cambiando a: {self.translators[self._active_index].get_provider_name()}"
                    )
                    last_exception = e
                    continue
                else:
                    # Último proveedor, esperar y reintentar
                    attempt += 1
                    last_exception = e
                    if attempt <= self.max_retries:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit en último proveedor (intento {attempt}/{self.max_retries}). "
                            f"Esperando {wait_time:.1f}s"
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        raise

            except TranslationTimeoutError as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(f"Timeout (intento {attempt}/{self.max_retries}). Reintentando...")
                    import time
                    time.sleep(wait_time)
                else:
                    # Timeout persistente -> intentar fallback
                    if self._active_index < len(self.translators) - 1:
                        self._last_fallback_reason = f"Timeout persistente: {e}"
                        self._active_index += 1
                        self._fallback_triggered = True
                        attempt = 0
                    else:
                        raise

            except AuthenticationError as e:
                # Error de autenticación -> probar siguiente proveedor
                if self._active_index < len(self.translators) - 1:
                    self._last_fallback_reason = f"Autenticación fallida: {e}"
                    self._active_index += 1
                    self._fallback_triggered = True
                    attempt = 0
                    last_exception = e
                    logger.warning(
                        f"Autenticación fallida en proveedor actual. "
                        f"Cambiando a: {self.translators[self._active_index].get_provider_name()}"
                    )
                    continue
                else:
                    logger.error(f"Autenticación fallida en último proveedor: {e}")
                    raise

            except TranslationAPIError as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(f"Error de API (intento {attempt}/{self.max_retries}): {e}")
                    import time
                    time.sleep(wait_time)
                else:
                    # Error persistente -> intentar fallback
                    if self._active_index < len(self.translators) - 1:
                        self._last_fallback_reason = f"Error de API persistente: {e}"
                        self._active_index += 1
                        self._fallback_triggered = True
                        attempt = 0
                    else:
                        raise

            except Exception as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(f"Error inesperado (intento {attempt}/{self.max_retries}): {e}")
                    import time
                    time.sleep(wait_time)
                else:
                    if self._active_index < len(self.translators) - 1:
                        self._last_fallback_reason = f"Error persistente: {e}"
                        self._active_index += 1
                        self._fallback_triggered = True
                        attempt = 0
                    else:
                        raise

        raise TranslationError(
            f"Falló la traducción después de {self.max_retries} intentos. "
            f"Último error: {last_exception}"
        )

    def was_fallback_triggered(self) -> bool:
        """Indica si se activó el fallback durante esta sesión."""
        return self._fallback_triggered

    def get_fallback_info(self) -> dict:
        """Devuelve información sobre el estado del fallback."""
        active = self.translators[self._active_index]
        return {
            "active_provider": active.get_provider_name(),
            "fallback_triggered": self._fallback_triggered,
            "last_fallback_reason": self._last_fallback_reason,
            "available_providers": [t.get_provider_name() for t in self.translators],
            "active_index": self._active_index,
        }

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> dict:
        """Estima el costo basado en el proveedor activo actual."""
        active = self.translators[self._active_index]
        estimate = active.estimate_cost(input_tokens, output_tokens)

        # Agregar información de fallback
        estimate["fallback_chain"] = [t.get_provider_name() for t in self.translators]
        estimate["active_provider"] = active.get_provider_name()

        if len(self.translators) > 1:
            estimate["notes"] = (
                estimate.get("notes", "") +
                f" | Fallback automático: {' -> '.join(t.get_provider_name() for t in self.translators)}"
            )

        return estimate
