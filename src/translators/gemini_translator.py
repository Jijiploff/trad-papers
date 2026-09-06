"""
Traductor basado en Google Gemini API.
Google ofrece una capa gratuita muy generosa:
- 1,000,000 tokens por día
- Límite de solicitudes por minuto (RPM) variable según el modelo/tier
- Sin costo para uso dentro de límites

Obtén tu API key gratuita en: https://aistudio.google.com/apikey
"""
import threading
import time
from collections import deque
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


class GeminiTranslator(BaseTranslator):
    """Traductor usando la API de Google Gemini (Generative AI)."""

    # Gemini Flash es GRATIS dentro de límites (Q3 2026):
    # - 1M tokens de entrada / día
    # - El límite de solicitudes por minuto (RPM) del free tier depende del
    #   modelo y puede ser TAN BAJO como 5 RPM (ver `requests_per_minute`
    #   más abajo) — NO asumas 15 RPM para todos los modelos.
    COST_PER_1M_INPUT = 0.00   # Gratis en free tier
    COST_PER_1M_OUTPUT = 0.00  # Gratis en free tier

    def __init__(
        self,
        api_key: str,
        # "gemini-flash-latest" es el alias oficial que Google mantiene
        # apuntando siempre al Flash estable más reciente. Si prefieres fijar
        # una versión específica (para que Google no te la cambie sin avisar),
        # usa por ejemplo "gemini-2.5-flash".
        model: str = "gemini-flash-latest",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        temperature: float = 0.2,
        # Límite de solicitudes por minuto del FREE TIER para el modelo activo.
        # Google ha estado reduciendo este límite en modelos más nuevos: en la
        # práctica ha llegado a ser tan bajo como 5 RPM. Configuralo un poco
        # por debajo del límite real (dejamos 4 por defecto) para tener
        # margen. Si tu proyecto tiene un tier de pago con más cupo, súbelo
        # (por ejemplo, vía config.yaml -> translation.gemini_requests_per_minute).
        requests_per_minute: int = 4,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature
        self._client = None
        self._model_instance = None

        # ---- Rate limiter compartido entre threads ----
        # El pipeline traduce chunks en paralelo (ThreadPoolExecutor). Sin
        # esto, varios hilos llaman a la API casi simultáneamente y todos
        # reciben 429 apenas se supera el RPM del free tier, en vez de
        # esperar su turno de forma ordenada.
        self.requests_per_minute = max(1, requests_per_minute)
        self._request_timestamps: deque = deque()
        self._rate_lock = threading.Lock()

    def _throttle(self) -> None:
        """Bloquea (sin fallar) hasta que haya un cupo dentro del límite de
        solicitudes por minuto configurado. Seguro para llamar desde varios
        threads a la vez."""
        window_seconds = 60.0
        while True:
            with self._rate_lock:
                now = time.monotonic()
                while self._request_timestamps and now - self._request_timestamps[0] > window_seconds:
                    self._request_timestamps.popleft()

                if len(self._request_timestamps) < self.requests_per_minute:
                    self._request_timestamps.append(now)
                    return

                wait_time = window_seconds - (now - self._request_timestamps[0]) + 0.05

            time.sleep(max(wait_time, 0.05))

    def _get_model(self):
        """Inicializa el cliente de Gemini de forma lazy."""
        if self._model_instance is None:
            try:
                import google.generativeai as genai
                from google.generativeai.types import GenerationConfig

                genai.configure(api_key=self.api_key)

                generation_config = GenerationConfig(
                    temperature=self.temperature,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8192,
                )

                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]

                self._model_instance = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                    system_instruction=self.SYSTEM_PROMPT,
                )

            except ImportError:
                raise TranslationError(
                    "El paquete 'google-generativeai' no está instalado. "
                    "Instálalo con: pip install google-generativeai>=0.8.0"
                )
        return self._model_instance

    def get_provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key) and len(self.api_key) > 20

    def translate_text(self, text: str, source_lang: str = "EN", target_lang: str = "ES") -> str:
        """Traduce un texto usando la API de Google Gemini."""
        if not self.is_available():
            raise AuthenticationError(
                "API key de Google Gemini no configurada. "
                "Obtén una gratis en: https://aistudio.google.com/apikey"
            )

        try:
            model = self._get_model()

            user_prompt = (
                f"Traduce el siguiente texto académico del inglés al español.\n\n"
                f"REGLAS ESTRICTAS - CUMPLELAS SIEMPRE:\n"
                f"1. NO traduzcas NADA que esté entre delimitadores matemáticos: $...$, $$...$$, \\(...\\), \\[...\\], \\begin{{equation}}...\\end{{equation}}, \\begin{{align}}...\\end{{align}}\n"
                f"2. NO traduzcas citas: [1], [2,3], (Author et al., 2020), \\cite{{...}}, \\citep{{...}}, \\citet{{...}}\n"
                f"3. NO traduzcas referencias cruzadas: \\ref{{...}}, \\eqref{{...}}, \\label{{...}}\n"
                f"4. NO traduzcas nombres de secciones si están en comandos LaTeX como \\section{{...}}\n"
                f"5. Mantén la terminología técnica precisa\n"
                f"6. Mantén los saltos de línea y estructura de párrafos\n"
                f"7. DEVUELVE SOLO LA TRADUCCIÓN, sin comentarios ni explicaciones\n\n"
                f"TEXTO A TRADUCIR:\n{text}"
            )

            # Esperar cupo disponible ANTES de llamar a la API, en vez de
            # llamar y descubrir un 429 después.
            self._throttle()

            response = model.generate_content(user_prompt)

            # Verificar si la respuesta fue bloqueada por seguridad
            if not response.candidates:
                feedback = response.prompt_feedback
                raise TranslationAPIError(
                    f"La solicitud fue bloqueada por filtros de seguridad. "
                    f"Motivo: {feedback.block_reason if feedback else 'Desconocido'}"
                )

            translated = response.text

            if not translated or not translated.strip():
                raise TranslationAPIError("Gemini devolvió una respuesta vacía")

            # Limpiar marcadores de código markdown si los agregó
            translated = translated.strip()
            if translated.startswith("```") and translated.endswith("```"):
                lines = translated.split("\n")
                translated = "\n".join(lines[1:-1]).strip()

            return translated

        except AuthenticationError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str or "rate limit" in error_str:
                raise RateLimitError(
                    f"Límite de Gemini alcanzado (modelo '{self.model}', "
                    f"{self.requests_per_minute} RPM configurado). "
                    f"Espera un momento o intenta mañana. Error: {e}"
                )
            elif "401" in error_str or "403" in error_str or "permission_denied" in error_str or "invalid" in error_str:
                raise AuthenticationError(f"API key de Gemini inválida o sin permisos: {e}")
            elif "timeout" in error_str or "timed out" in error_str or "deadline_exceeded" in error_str:
                raise TranslationTimeoutError(f"Timeout en Gemini: {e}")
            elif "404" in error_str or "not found" in error_str:
                # Esto casi siempre significa que el nombre del modelo configurado
                # ya no existe / fue retirado por Google. No tiene sentido
                # reintentar el mismo request: siempre volverá a fallar igual.
                raise TranslationAPIError(
                    f"El modelo '{self.model}' no existe o no está disponible para "
                    f"esta API key/región (404). Este error NO se soluciona reintentando: "
                    f"actualiza el nombre del modelo (por ejemplo a 'gemini-flash-latest' "
                    f"o 'gemini-2.5-flash') en la configuración. Error original: {e}"
                )
            else:
                raise TranslationAPIError(f"Error en Gemini API: {e}")

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> dict:
        """Estima el costo - Gemini Flash es gratuito en free tier."""
        output = output_tokens or input_tokens
        total = input_tokens + output

        return {
            "provider": f"google-gemini ({self.model})",
            "input_tokens": input_tokens,
            "output_tokens": output,
            "total_tokens": total,
            "estimated_cost_usd": 0.0,
            "currency": "USD",
            "free_tier": True,
            "free_tier_limits": (
                f"Free tier: 1,000,000 tokens/día. Límite configurado de "
                f"{self.requests_per_minute} solicitudes/minuto (ajústalo si tu "
                f"tier real permite más o menos)."
            ),
            "notes": (
                "Obtén tu API key GRATUITA en https://aistudio.google.com/apikey. "
                "Sin tarjeta de crédito requerida para el free tier."
            ),
        }