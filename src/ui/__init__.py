# __init__.py
"""
Módulo UI: componentes y estilos para la interfaz Streamlit.
"""
from src.ui.styles import get_css
from src.ui.components import (
    inject_styles,
    render_header,
    render_file_table,
    render_side_by_side_preview,
    render_provider_selector,
    render_cost_estimate,
    render_cache_stats,
    render_status_badge,
    render_theme_selector,  # ← Nuevo componente
)

__all__ = [
    "get_css",
    "inject_styles",
    "render_header",
    "render_file_table",
    "render_side_by_side_preview",
    "render_provider_selector",
    "render_cost_estimate",
    "render_cache_stats",
    "render_status_badge",
    "render_theme_selector",
]