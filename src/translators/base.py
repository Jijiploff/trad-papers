"""
Clase base abstracta para motores de traducción.
Define la interfaz común y lógica compartida (reintentos, rate limiting, etc.).
"""
from abc import ABC, abstractmethod
import time
import random
from typing import Optional, Callable

from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationError(Exception):
    """Error genérico durante la traducción."""
    pass


class TranslationTimeoutError(TranslationError):
    """La traducción excedió el tiempo límite."""
    pass


class TranslationAPIError(TranslationError):
    """Error devuelto por la API del proveedor."""
    pass


class RateLimitError(TranslationAPIError):
    """Se excedió el límite de tasa de la API."""
    pass


class AuthenticationError(TranslationAPIError):
    """Error de autenticación con la API."""
    pass


class BaseTranslator(ABC):
    """
    Clase base abstracta para todos los proveedores de traducción.
    Incluye lógica común de reintentos con backoff exponencial y manejo de rate limits.
    """

    # Prompt del sistema para traducción académica
    SYSTEM_PROMPT = r"""Eres un traductor profesional especializado en textos académicos y científicos.
Instrucciones estrictas:
1. Traduce del inglés al español manteniendo la terminología técnica precisa.
2. PRESERVA absolutamente todos los elementos entre delimitadores matemáticos: $...$, $$...$$, \(...\), \[...\], \begin{equation}...\end{equation}, etc. No traduzcas ni modifiques el contenido matemático.
3. PRESERVA las citas bibliográficas tal cual aparecen: [1], (Author et al., 2020), \cite{...}, \citep{...}, \citet{...}.
4. PRESERVA las referencias cruzadas: \ref{...}, \eqref{...}, \label{...}.
5. PRESERVA los marcadores de tablas y figuras: [Tabla], [Figura], \begin{table}, \begin{figure}.
6. Usa un español formal y académico apropiado para revistas científicas.
7. No añadas comentarios, explicaciones ni notas. Devuelve SOLO el texto traducido.
8. Mantén la estructura de párrafos y saltos de línea originales.
9. Cuando encuentres nombres propios, títulos de revistas o conferencias, mantenlos en su idioma original si es la convención.
10. Asegúrate de que las unidades, símbolos y acrónimos técnicos se traduzcan correctamente o se mantengan según la norma ISO.
11. Si recibes marcadores como <<<ELEMENT_0>>>, consérvalos exactamente y devuelve cada bloque en el mismo orden."""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        timeout: int = 120,
        rate_limit_delay: float = 1.0,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    @abstractmethod
    def translate_text(self, text: str, source_lang: str = "EN", target_lang: str = "ES") -> str:
        """
        Traduce un fragmento de texto.
        Implementación específica de cada proveedor.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Devuelve el nombre identificador del proveedor."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está configurado y accesible."""
        pass

    def translate_with_retry(
        self,
        text: str,
        source_lang: str = "EN",
        target_lang: str = "ES",
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """
        Traduce texto con reintentos automáticos y manejo de rate limits.

        Args:
            text: Texto a traducir
            source_lang: Idioma origen
            target_lang: Idioma destino
            progress_callback: Función opcional para reportar progreso (0.0 a 1.0)

        Returns:
            Texto traducido
        """
        if not text or not text.strip():
            return text

        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                # Respetar rate limit
                self._enforce_rate_limit()

                result = self.translate_text(text, source_lang, target_lang)

                if progress_callback:
                    progress_callback(1.0)

                return result

            except RateLimitError as e:
                attempt += 1
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Rate limit alcanzado (intento {attempt}/{self.max_retries}). "
                    f"Esperando {wait_time:.1f}s: {e}"
                )
                time.sleep(wait_time)

            except TranslationTimeoutError as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(
                        f"Timeout (intento {attempt}/{self.max_retries}). "
                        f"Reintentando en {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                else:
                    raise

            except AuthenticationError as e:
                # No reintentar errores de autenticación
                logger.error(f"Error de autenticación: {e}")
                raise

            except TranslationAPIError as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(
                        f"Error de API (intento {attempt}/{self.max_retries}): {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                attempt += 1
                last_exception = e
                if attempt <= self.max_retries:
                    wait_time = self.retry_delay * attempt
                    logger.warning(
                        f"Error inesperado (intento {attempt}/{self.max_retries}): {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise

        raise TranslationError(
            f"Falló la traducción después de {self.max_retries} intentos. "
            f"Último error: {last_exception}"
        )

    def _enforce_rate_limit(self) -> None:
        """Asegura que no se exceda el límite de tasa entre solicitudes."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            wait = self.rate_limit_delay - elapsed
            time.sleep(wait)
        self._last_request_time = time.time()

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> dict:
        """
        Estima el costo de traducción para un número dado de tokens.
        Cada proveedor debe sobreescribir este método con sus tarifas.
        """
        return {
            "provider": self.get_provider_name(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens or input_tokens,
            "total_tokens": input_tokens + (output_tokens or input_tokens),
            "estimated_cost_usd": 0.0,
            "currency": "USD",
        }
