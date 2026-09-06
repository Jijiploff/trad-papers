"""
Traductor con fallback automático.
Intenta traducir con el proveedor primario (Gemini) y si falla por:
- Límite de cuota / rate limit alcanzado
- Timeout
- Error de API no recuperable
- Proveedor no disponible

Automáticamente cambia al proveedor secundario (DeepL) sin intervención del usuario.
"""
import re
import time
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

# Fragmentos de mensaje de error que indican un problema de CONFIGURACIÓN
# (modelo inexistente, endpoint incorrecto, etc.) en vez de un problema
# transitorio. Reintentar estos errores es inútil: siempre van a volver a
# fallar exactamente igual, así que conviene saltar directo al fallback.
_NON_RETRYABLE_HINTS = ("404", "not found", "no existe", "no está disponible")

# Fragmentos de mensaje que indican una cuota agotada del PERÍODO DE
# FACTURACIÓN (mensual/diaria) en vez de un límite transitorio por minuto.
# Esto NO se arregla esperando unos segundos y reintentando: hay que esperar
# al próximo ciclo de facturación (o cambiar de plan).
_PERMANENT_QUOTA_HINTS = (
    "billing period",
    "periodo de facturación",
    "período de facturación",
    "monthly quota",
    "cuota mensual",
    # Límites DIARIOS (RPD - Requests Per Day). Un límite diario agotado
    # tampoco se soluciona esperando el "retry_delay" corto que sugiere la
    # API para el límite POR MINUTO: hay que esperar hasta el próximo día.
    "perday",
    "per day",
    "requests per day",
    "requestsperday",
    "daily quota",
    "cuota diaria",
)

# Patrones para extraer el tiempo de espera sugerido por la propia API
# (Gemini, por ejemplo, devuelve "retry_delay { seconds: 22 }" o
# "Please retry in 22.98s").
_RETRY_SECONDS_PATTERNS = [
    re.compile(r"retry_delay\s*\{\s*seconds:\s*(\d+)"),
    re.compile(r"retry in ([\d.]+)\s*s"),
]


def _is_non_retryable_config_error(error_str_lower: str) -> bool:
    """True si el mensaje de error indica un problema de configuración
    (modelo inexistente/retirado, endpoint incorrecto) que NUNCA se resuelve
    reintentando el mismo request."""
    return any(hint in error_str_lower for hint in _NON_RETRYABLE_HINTS)


def _is_permanent_quota_error(error_str_lower: str) -> bool:
    """True si el error es una cuota agotada del período de facturación
    (mensual/diaria) y no un límite transitorio por minuto."""
    return any(hint in error_str_lower for hint in _PERMANENT_QUOTA_HINTS)


def _extract_retry_seconds(error_str_lower: str) -> Optional[float]:
    """Intenta extraer cuántos segundos sugiere esperar la API antes de
    reintentar. Devuelve None si no se encuentra ninguna pista."""
    for pattern in _RETRY_SECONDS_PATTERNS:
        match = pattern.search(error_str_lower)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


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
        # Índices de proveedores marcados como agotados (cuota del período de
        # facturación excedida) durante esta sesión. Una vez marcado, no se
        # vuelve a intentar con ese proveedor hasta reiniciar la app — no
        # tiene caso perder 3 reintentos con backoff en CADA chunk sabiendo
        # de antemano que va a fallar igual.
        self._exhausted_indices: set = set()

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

    def _first_available_index(self, start: int) -> Optional[int]:
        """Primer índice >= start que no esté marcado como agotado. None si
        no queda ninguno."""
        for idx in range(start, len(self.translators)):
            if idx not in self._exhausted_indices:
                return idx
        return None

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
            # Hacer fallback para errores de servidor, cuota o configuración
            # (modelo inexistente/retirado -> "404"/"not found")
            if any(kw in error_str for kw in ['quota', 'exhausted', 'limit', 'server', '500', '503', 'unavailable', 'overloaded']):
                return True
            if _is_non_retryable_config_error(error_str):
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
        idx = self._active_index

        while idx < len(self.translators):
            if idx in self._exhausted_indices:
                idx += 1
                continue

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
                error_str = str(e).lower()

                if isinstance(e, RateLimitError) and _is_permanent_quota_error(error_str):
                    self._exhausted_indices.add(idx)

                has_next = self._first_available_index(idx + 1) is not None

                if self._should_fallback(e) and has_next:
                    self._last_fallback_reason = str(e)
                    logger.warning(
                        f"Proveedor {provider_name} falló ({type(e).__name__}: {e}). "
                        f"Intentando fallback..."
                    )
                    idx += 1
                    continue
                else:
                    # No hacer fallback o no hay más proveedores
                    logger.error(
                        f"Proveedor {provider_name} falló sin posibilidad de fallback: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise

        # Si llegamos aquí, todos los proveedores fallaron (o están agotados)
        raise TranslationError(
            f"Todos los proveedores de traducción fallaron o están agotados. "
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

        # IMPORTANTE: empezar SIEMPRE desde el primer proveedor no agotado
        # (normalmente el primario/gratuito, p. ej. Gemini) en cada chunk
        # nuevo — NO seguir desde donde se quedó el chunk anterior. Un
        # límite por MINUTO es transitorio: para cuando llega el siguiente
        # chunk (segundos/minutos después) puede que ya se haya recuperado,
        # así que vale la pena volver a intentarlo en vez de quedarse
        # "pegado" para siempre en el proveedor de fallback.
        avail = self._first_available_index(0)
        if avail is None:
            exhausted_names = [
                self.translators[i].get_provider_name() for i in self._exhausted_indices
            ]
            raise TranslationError(
                "Todos los proveedores de traducción disponibles agotaron su cuota "
                f"del período (diaria/mensual): {', '.join(exhausted_names) or 'desconocido'}. "
                "Espera a que se renueve la cuota (día/mes siguiente) o agrega otro proveedor."
            )
        self._active_index = avail

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
                error_str = str(e).lower()
                is_permanent = _is_permanent_quota_error(error_str)
                if is_permanent:
                    self._exhausted_indices.add(self._active_index)

                next_idx = self._first_available_index(self._active_index + 1)

                if next_idx is not None:
                    # Hay otro proveedor disponible: cambiar.
                    self._last_fallback_reason = str(e)
                    self._active_index = next_idx
                    self._fallback_triggered = True
                    logger.warning(
                        f"Rate limit en proveedor actual"
                        f"{' (cuota del período agotada)' if is_permanent else ''}. "
                        f"Cambiando a: {self.translators[self._active_index].get_provider_name()}"
                    )
                    last_exception = e
                    current_provider_index = self._active_index
                    attempt = 0
                    continue

                elif not is_permanent:
                    # Único proveedor disponible y el límite es TRANSITORIO
                    # (por minuto): esperar el tiempo sugerido por la propia
                    # API y reintentar el MISMO proveedor.
                    attempt += 1
                    last_exception = e
                    if attempt <= self.max_retries:
                        suggested = _extract_retry_seconds(error_str)
                        wait_time = suggested if suggested is not None else self.retry_delay * (2 ** attempt)
                        wait_time = min(max(wait_time, 0.5), 60)
                        logger.warning(
                            f"Rate limit en último proveedor disponible "
                            f"(intento {attempt}/{self.max_retries}). Esperando {wait_time:.1f}s"
                        )
                        time.sleep(wait_time)
                    else:
                        raise

                else:
                    # Único proveedor disponible y la cuota del PERÍODO DE
                    # FACTURACIÓN está agotada: reintentar no sirve de nada
                    # hasta el próximo ciclo, así que fallamos de una vez en
                    # vez de hacer 3 reintentos con backoff inútiles.
                    logger.error(
                        f"Cuota del período de facturación agotada en el único "
                        f"proveedor disponible: {e}"
                    )
                    raise

            except TranslationTimeoutError as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(f"Timeout (intento {attempt}/{self.max_retries}). Reintentando...")
                    time.sleep(wait_time)
                else:
                    # Timeout persistente -> intentar fallback
                    next_idx = self._first_available_index(self._active_index + 1)
                    if next_idx is not None:
                        self._last_fallback_reason = f"Timeout persistente: {e}"
                        self._active_index = next_idx
                        self._fallback_triggered = True
                        attempt = 0
                    else:
                        raise

            except AuthenticationError as e:
                # Error de autenticación -> probar siguiente proveedor
                next_idx = self._first_available_index(self._active_index + 1)
                if next_idx is not None:
                    self._last_fallback_reason = f"Autenticación fallida: {e}"
                    self._active_index = next_idx
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
                error_str = str(e).lower()

                # Errores de configuración (p. ej. modelo retirado/inexistente,
                # 404) NUNCA se arreglan reintentando el mismo request: saltamos
                # directo al fallback (o fallamos ya) en vez de perder tiempo
                # con 3 reintentos idénticos.
                if _is_non_retryable_config_error(error_str):
                    last_exception = e
                    next_idx = self._first_available_index(self._active_index + 1)
                    if next_idx is not None:
                        self._last_fallback_reason = f"Error de configuración: {e}"
                        logger.error(
                            f"Error de configuración no reintentable en proveedor actual "
                            f"({e}). Saltando directo a: "
                            f"{self.translators[next_idx].get_provider_name()}"
                        )
                        self._active_index = next_idx
                        self._fallback_triggered = True
                        attempt = 0
                        continue
                    else:
                        logger.error(f"Error de configuración en el último proveedor: {e}")
                        raise

                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(f"Error de API (intento {attempt}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    # Error persistente -> intentar fallback
                    next_idx = self._first_available_index(self._active_index + 1)
                    if next_idx is not None:
                        self._last_fallback_reason = f"Error de API persistente: {e}"
                        self._active_index = next_idx
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
                    time.sleep(wait_time)
                else:
                    next_idx = self._first_available_index(self._active_index + 1)
                    if next_idx is not None:
                        self._last_fallback_reason = f"Error persistente: {e}"
                        self._active_index = next_idx
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
            "exhausted_providers": [
                self.translators[i].get_provider_name() for i in self._exhausted_indices
            ],
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