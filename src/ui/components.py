# components.py - Versión mejorada con selector de tema

"""
Componentes UI reutilizables para la aplicación Streamlit.
Proporciona helpers para renderizar tablas, tarjetas de estado,
paneles de comparación y navegación por secciones.
"""
import streamlit as st
from typing import List, Dict, Any, Optional
import difflib

from src.core.models import Document, TranslationStatus, SectionType
from src.ui.styles import get_css


def inject_styles(dark_mode: bool = None) -> None:
    """Inyecta los estilos CSS personalizados en la aplicación."""
    if dark_mode is None:
        dark_mode = st.session_state.get("dark_mode", False)
    st.markdown(get_css(dark_mode), unsafe_allow_html=True)


def render_theme_selector() -> None:
    """Renderiza el selector de tema (claro/oscuro)."""
    # Inicializar estado
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    
    # Obtener icono según modo
    icon = "🌙" if not st.session_state.dark_mode else "☀️"
    label = "Modo oscuro" if not st.session_state.dark_mode else "Modo claro"
    
    # Botón en la barra lateral o en la parte superior
    if st.sidebar.button(
        f"{icon} {label}",
        help="Cambiar entre tema claro y oscuro",
        use_container_width=True,
    ):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()


def render_header() -> None:
    """Renderiza el encabezado principal de la aplicación."""
    st.markdown("""
        <div class="app-header">
            <h1>📄 Paper Translator</h1>
            <p>Traducción masiva de papers científicos del inglés al español con preservación de formato</p>
        </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: TranslationStatus) -> str:
    """Devuelve el HTML de un badge de estado."""
    badge_map = {
        TranslationStatus.PENDING: ('badge-secondary', '⏳ Pendiente'),
        TranslationStatus.LOADING: ('badge-info', '📥 Cargando'),
        TranslationStatus.LOADED: ('badge-info', '📄 Cargado'),
        TranslationStatus.CHUNKING: ('badge-warning', '✂️ Dividiendo'),
        TranslationStatus.TRANSLATING: ('badge-warning', '🔄 Traduciendo'),
        TranslationStatus.TRANSLATED: ('badge-info', '✅ Traducido'),
        TranslationStatus.EXPORTING: ('badge-info', '📤 Exportando'),
        TranslationStatus.COMPLETED: ('badge-success', '✨ Completado'),
        TranslationStatus.ERROR: ('badge-error', '❌ Error'),
        TranslationStatus.CACHED: ('badge-success', '💾 Desde caché'),
    }
    css_class, label = badge_map.get(status, ('badge-secondary', str(status.value)))
    return f'<span class="badge {css_class}">{label}</span>'


def render_file_table(
    documents: List[Document],
    selected_ids: Dict[str, bool],
) -> Dict[str, bool]:
    """
    Renderiza una tabla con los documentos cargados y checkboxes de selección.
    """
    if not documents:
        st.info("📂 No hay archivos cargados. Usa el área de arriba para subir documentos.")
        return selected_ids

    st.subheader(f"📊 Archivos cargados ({len(documents)})")
    st.markdown("Selecciona los documentos que deseas traducir:")

    # Contenedor con scroll
    st.markdown('<div class="file-table-container">', unsafe_allow_html=True)

    # Crear encabezados
    cols = st.columns([0.5, 3, 1, 1, 1.5, 1.2])
    headers = ["", "📄 Nombre", "📁 Tipo", "📦 Tamaño", "📊 Tokens aprox.", "📌 Estado"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    st.markdown("---")

    updated_selections = {}

    for doc in documents:
        cols = st.columns([0.5, 3, 1, 1, 1.5, 1.2])

        # Checkbox
        with cols[0]:
            is_selected = selected_ids.get(doc.doc_id, True)
            updated_selections[doc.doc_id] = st.checkbox(
                "Seleccionar",
                value=is_selected,
                key=f"select_{doc.doc_id}",
                label_visibility="collapsed",
            )

        # Nombre
        with cols[1]:
            st.text(doc.filename)

        # Tipo
        with cols[2]:
            st.markdown(f"`{doc.file_type.value.upper()}`")

        # Tamaño
        with cols[3]:
            if doc.file_size_mb > 1:
                st.text(f"{doc.file_size_mb:.2f} MB")
            else:
                st.text(f"{doc.file_size_kb:.1f} KB")

        # Tokens / Páginas
        with cols[4]:
            info_parts = []
            if doc.estimated_tokens:
                info_parts.append(f"{doc.estimated_tokens:,} tok")
            if doc.page_count:
                info_parts.append(f"{doc.page_count} pág")
            st.text(" | ".join(info_parts) if info_parts else "-")

        # Estado
        with cols[5]:
            st.markdown(render_status_badge(doc.status), unsafe_allow_html=True)

        # Barra de progreso si está traduciendo
        if doc.status in (TranslationStatus.TRANSLATING, TranslationStatus.LOADING):
            progress = doc.progress or 0.0
            st.progress(progress, text=f"Progreso: {progress*100:.0f}%")

        # Mensaje de error si existe
        if doc.status == TranslationStatus.ERROR and doc.error_message:
            st.markdown(
                f'<div class="status-card error">❌ {doc.error_message}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

    st.markdown('</div>', unsafe_allow_html=True)
    return updated_selections


# components.py - Sección render_side_by_side_preview mejorada

def render_side_by_side_preview(document: Document) -> None:
    """Renderiza un panel dividido con el texto original y la traducción."""
    if not document.sections:
        st.warning("⚠️ Este documento no tiene secciones para previsualizar.")
        return

    st.subheader(f"🔍 Previsualización: {document.filename}")

    # Navegación por secciones
    section_options = []
    for section in document.sections:
        label = section.title or section.section_type.value.capitalize()
        section_options.append((section.section_id, label))

    if not section_options:
        return

    # Selector de sección
    section_ids = [s[0] for s in section_options]
    section_labels = [s[1] for s in section_options]

    # Inicializar sección seleccionada
    if f"active_section_{document.doc_id}" not in st.session_state:
        st.session_state[f"active_section_{document.doc_id}"] = section_ids[0]

    # Botones de navegación - más compactos
    st.markdown('<div class="section-nav">', unsafe_allow_html=True)
    
    # Mostrar botones en filas de 8 para que ocupen menos espacio
    cols_per_row = 8
    for i in range(0, len(section_ids), cols_per_row):
        cols = st.columns(min(cols_per_row, len(section_ids) - i))
        for j, (sec_id, label) in enumerate(zip(
            section_ids[i:i+cols_per_row],
            section_labels[i:i+cols_per_row]
        )):
            with cols[j]:
                is_active = st.session_state[f"active_section_{document.doc_id}"] == sec_id
                # Botones más pequeños
                if st.button(
                    label[:20] + "..." if len(label) > 20 else label,  # Truncar nombres largos
                    key=f"secbtn_{document.doc_id}_{sec_id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state[f"active_section_{document.doc_id}"] = sec_id
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Obtener sección activa
    active_id = st.session_state[f"active_section_{document.doc_id}"]
    active_section = next((s for s in document.sections if s.section_id == active_id), None)

    if not active_section:
        return

    # Panel side-by-side con scroll limitado
    original_text = active_section.original_text
    translated_text = active_section.translated_text or "*[Aún no traducido]*"

    # Opciones de visualización - más compactas
    view_mode = st.radio(
        "Modo de visualización:",
        ["📖 Lado a lado", "📝 Solo original", "🌐 Solo traducción"],
        horizontal=True,
        key=f"viewmode_{document.doc_id}",
    )

    # Altura máxima fija con scroll
    PANEL_HEIGHT = "350px"  # Altura reducida para que no ocupe toda la pantalla

    if view_mode == "📖 Lado a lado":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="diff-panel original" style="height: {PANEL_HEIGHT};">', unsafe_allow_html=True)
            st.markdown("#### 📄 Original (Inglés)")
            # Mostrar solo primeras líneas con scroll
            preview_text = _get_preview_text(original_text, max_lines=50)
            st.markdown(
                f'<div class="diff-content">{_format_text(preview_text)}</div>',
                unsafe_allow_html=True,
            )
            # Indicador si hay más contenido
            if len(original_text.splitlines()) > 50:
                st.caption("📜 ... (desplázate para ver más)")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="diff-panel translated" style="height: {PANEL_HEIGHT};">', unsafe_allow_html=True)
            st.markdown("#### 🌐 Traducción (Español)")
            preview_text = _get_preview_text(translated_text, max_lines=50)
            st.markdown(
                f'<div class="diff-content">{_format_text(preview_text)}</div>',
                unsafe_allow_html=True,
            )
            if len(translated_text.splitlines()) > 50:
                st.caption("📜 ... (desplázate para ver más)")
            st.markdown('</div>', unsafe_allow_html=True)

    elif view_mode == "📝 Solo original":
        st.markdown(f'<div class="diff-panel original" style="height: {PANEL_HEIGHT};">', unsafe_allow_html=True)
        st.markdown("#### 📄 Original (Inglés)")
        preview_text = _get_preview_text(original_text, max_lines=50)
        st.markdown(
            f'<div class="diff-content">{_format_text(preview_text)}</div>',
            unsafe_allow_html=True,
        )
        if len(original_text.splitlines()) > 50:
            st.caption("📜 ... (desplázate para ver más)")
        st.markdown('</div>', unsafe_allow_html=True)

    else:  # Solo traducción
        st.markdown(f'<div class="diff-panel translated" style="height: {PANEL_HEIGHT};">', unsafe_allow_html=True)
        st.markdown("#### 🌐 Traducción (Español)")
        preview_text = _get_preview_text(translated_text, max_lines=50)
        st.markdown(
            f'<div class="diff-content">{_format_text(preview_text)}</div>',
            unsafe_allow_html=True,
        )
        if len(translated_text.splitlines()) > 50:
            st.caption("📜 ... (desplázate para ver más)")
        st.markdown('</div>', unsafe_allow_html=True)


def _get_preview_text(text: str, max_lines: int = 50) -> str:
    """Obtiene solo las primeras N líneas del texto para previsualización."""
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + "\n\n... (texto truncado para previsualización)"


def _format_text(text: str) -> str:
    """Formatea texto para visualización HTML, preservando saltos de línea."""
    import html
    escaped = html.escape(text)
    # Preservar saltos de línea
    escaped = escaped.replace('\n', '<br>')
    # Preservar espacios
    escaped = escaped.replace(' ', '&nbsp;')
    return escaped


def _generate_diff_html(original: str, translated: str) -> str:
    """Genera HTML con diferencias resaltadas entre dos textos."""
    # Comparar línea por línea
    orig_lines = original.splitlines()
    trans_lines = translated.splitlines()

    differ = difflib.HtmlDiff(wrapcolumn=80)
    diff_table = differ.make_table(orig_lines, trans_lines, "Original", "Traducido", context=True)

    # Obtener modo oscuro
    dark_mode = st.session_state.get("dark_mode", False)
    bg_color = "#1a2234" if dark_mode else "#f8f9fa"
    text_color = "#e5e7eb" if dark_mode else "#1a202c"
    
    return f"""
    <div style="overflow-x: auto; font-size: 0.85rem; background: {bg_color}; padding: 1rem; border-radius: 8px; color: {text_color};">
        {diff_table}
    </div>
    """


def render_provider_selector(
    available_providers: Dict[Any, bool],
    default: str = "gemini",
) -> str:
    """Renderiza el selector de proveedor de traducción."""
    st.subheader("🔧 Motor de traducción")

    provider_info = {
        "gemini": {
            "name": "🆓 Google Gemini 1.5 Flash",
            "description": "1M tokens/día GRATIS. Si se agota, pasa AUTOMÁTICAMENTE a DeepL.",
            "available": available_providers.get("gemini", False),
            "color": "#3b82f6",
        },
        "deepl": {
            "name": "🔄 DeepL API (Fallback)",
            "description": "Plan gratuito: 500K caracteres/mes. Se activa solo si Gemini falla.",
            "available": available_providers.get("deepl", False),
            "color": "#10b981",
        },
        "openai": {
            "name": "💎 OpenAI GPT-4o (Último recurso)",
            "description": "Máxima calidad. Pago por uso. Último en la cadena de fallback.",
            "available": available_providers.get("openai", False),
            "color": "#f59e0b",
        },
    }

    # Default: gemini siempre primero
    if default not in provider_info:
        default = "gemini"

    selected = st.radio(
        "Selecciona el proveedor principal:",
        list(provider_info.keys()),
        format_func=lambda k: provider_info[k]["name"],
        index=list(provider_info.keys()).index(default) if default in provider_info else 0,
        help="Sistema de fallback automático: Gemini → DeepL → OpenAI. Si uno falla, pasa al siguiente.",
    )

    info = provider_info[selected]
    status_icon = "✅" if info["available"] else "⚠️"
    status_text = "Configurado y listo" if info["available"] else "No configurado - revisa config.yaml"

    st.markdown(
        f'<div class="status-card {"success" if info["available"] else "warning"}">'
        f'<strong>{status_icon} {status_text}</strong><br>'
        f'<small>{info["description"]}</small>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Mostrar información de la cadena de fallback
    st.markdown(
        '<div class="status-card info">'
        '<strong>🔄 Sistema de Fallback Automático</strong><br>'
        '<small>Gemini (primario) → DeepL (secundario) → OpenAI (terciario)<br>'
        'Si Gemini se queda sin tokens o no responde, la app cambiará automáticamente al siguiente proveedor sin intervención.</small>'
        '</div>',
        unsafe_allow_html=True,
    )

    return selected


def render_cost_estimate(
    total_tokens: int,
    translator,
) -> None:
    """Muestra una estimación de costo para la traducción."""
    if total_tokens <= 0:
        return

    estimate = translator.estimate_cost(total_tokens)

    st.subheader("💰 Estimación de costo")

    cost = estimate.get("estimated_cost_usd", 0)
    provider = estimate.get("provider", "N/A")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Tokens totales", f"{total_tokens:,}")
    with col2:
        st.metric("🔌 Proveedor", provider)
    with col3:
        if cost == 0:
            st.metric("💵 Costo estimado", "🆓 $0.00 USD")
        else:
            st.metric("💵 Costo estimado", f"${cost:.4f} USD")

    if estimate.get("free_tier"):
        st.success("🎉 ¡Este proveedor tiene una capa gratuita generosa!")

    if "free_tier_limits" in estimate:
        st.info(f"📋 Límites gratuitos: {estimate['free_tier_limits']}")

    if "notes" in estimate:
        st.caption(estimate["notes"])


def render_cache_stats(cache_stats: Dict[str, Any]) -> None:
    """Muestra estadísticas de la caché."""
    with st.expander("💾 Estadísticas de caché"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📁 Entradas en caché", cache_stats.get("entry_count", 0))
        with col2:
            size_mb = cache_stats.get("total_size_mb", 0)
            st.metric("📦 Tamaño total", f"{size_mb:.2f} MB")