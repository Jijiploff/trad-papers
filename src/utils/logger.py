"""
Configuración centralizada de logging para toda la aplicación.
Proporciona loggers estructurados con salida a consola y archivo.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "paper_translator",
    log_dir: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Configura y devuelve un logger con handlers de consola y archivo.

    Args:
        name: Nombre del logger
        log_dir: Directorio para archivos de log. Si es None, solo consola.
        level: Nivel de logging mínimo

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Evitar duplicar handlers si ya fue configurado
    if logger.handlers:
        return logger

    # Formato común
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler de archivo
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_path / "app.log",
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "paper_translator") -> logging.Logger:
    """Obtiene un logger existente o crea uno nuevo con configuración por defecto."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
