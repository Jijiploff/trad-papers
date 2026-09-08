"""
Módulo de configuración. Carga credenciales y parámetros desde config.yaml
o variables de entorno, con valores por defecto razonables.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


DEFAULT_CONFIG = {
    "app": {
        "name": "Paper Translator",
        "max_files": 20,
        "max_file_size_mb": 50,
        "cache_dir": "cache",
        "log_dir": "logs",
        "export_dir": "exports",
    },
    "translation": {
        "chunk_size_tokens": 3500,
        "chunk_overlap_tokens": 200,
        "max_workers": 4,
        "request_timeout_seconds": 120,
        "max_retries": 3,
        "retry_delay_seconds": 2,
        "rate_limit_delay_seconds": 1.0,
        "source_lang": "EN",
        "target_lang": "ES",
    },
    "mineru": {
        "timeout_per_chunk_seconds": 600,
        "retries": 1,
        "pages_per_chunk": 5,
        "max_pages": 20,
        "max_file_size_mb": 5,
        "require_mineru": True,
        "workers": 2,
    },
    "llama": {
        "api_key": "",
        "tier": "cost_effective",
        "version": "latest",
        "enabled": True,
        "timeout_seconds": 600,
    },
    "providers": {
        "openai": {
            "api_key": "",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.3,
        },
        "deepl": {
            "api_key": "",
            "base_url": "https://api.deepl.com/v2",
            "formality": "default",
        },
        "gemini": {
            "api_key": "",
            "model": "gemini-3.1-flash-lite",
            "temperature": 0.2,
        },
    },
}


def find_config_path() -> Optional[Path]:
    """Busca el archivo config.yaml en ubicaciones comunes."""
    candidates = [
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        Path(__file__).parent.parent.parent / "config.yaml",
        Path.home() / ".paper_translator" / "config.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga la configuración desde un archivo YAML y combina con valores por defecto.
    Las variables de entorno tienen prioridad sobre el archivo.
    """
    config = _deep_copy(DEFAULT_CONFIG)

    # Cargar desde archivo
    path = Path(config_path) if config_path else find_config_path()
    if path and path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, file_config)
        except Exception as e:
            print(f"Warning: No se pudo cargar {path}: {e}")

    # Sobreescribir con variables de entorno
    env_mappings = {
        "OPENAI_API_KEY": ("providers", "openai", "api_key"),
        "DEEPL_API_KEY": ("providers", "deepl", "api_key"),
        "GEMINI_API_KEY": ("providers", "gemini", "api_key"),
        "LLAMA_CLOUD_API_KEY": ("llama", "api_key"),
    }
    for env_var, keys in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            _set_nested(config, keys, value)

    return config


def _deep_copy(d: Dict[str, Any]) -> Dict[str, Any]:
    import copy
    return copy.deepcopy(d)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Fusiona dos diccionarios recursivamente."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _set_nested(d: Dict[str, Any], keys: tuple, value: Any) -> None:
    current = d
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value
