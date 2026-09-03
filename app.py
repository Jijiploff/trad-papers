#!/usr/bin/env python3
"""
Paper Translator - Aplicación Streamlit para traducción masiva de papers científicos.

Esta es la aplicación principal que integra todos los módulos:
- Carga de archivos (PDF, DOCX, TXT, LaTeX)
- Selección inteligente con tabla de metadatos
- Traducción paralela con múltiples proveedores
- Previsualización lado a lado
- Exportación en formatos originales o ZIP
- Modo oscuro/claro integrado
"""
import sys
import os
import uuid
import io
import zipfile
from pathlib import Path
from typing import List, Dict, Optional

# Asegurar que el directorio del proyecto esté en el path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from src.core.models import (
    Document,
    FileType,
    TranslationProvider,
    TranslationStatus,
)
from src.core.pipeline import TranslationPipeline, TranslationProgress
from src.processors import ProcessorFactory
from src.translators import TranslatorFactory
from src.translators.fallback_translator import FallbackTranslator
from src.utils.cache import TranslationCache
from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.utils.exporter import DocumentExporter
from src.ui import (
    inject_styles,
    render_header,
    render_file_table,
    render_side_by_side_preview,
    render_provider_selector,
    render_cost_estimate,
    render_cache_stats,
    render_theme_selector,  # Nuevo componente
)


# =============================================================================
# Configuración de la página
# =============================================================================
st.set_page_config(
    page_title="Paper Translator - Traducción de documentos académicos",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# Inicialización de estado y componentes
# =============================================================================
@st.cache_resource
def initialize_app():
    """Inicializa componentes que persisten entre reruns."""
    config = load_config()

    # Configurar logging
    log_dir = config.get("app", {}).get("log_dir", "logs")
    logger = setup_logger("paper_translator", log_dir=log_dir)
    logger.info("=" * 60)
    logger.info("Paper Translator iniciado")

    # Inicializar caché
    cache_dir = config.get("app", {}).get("cache_dir", "cache")
    cache = TranslationCache(cache_dir=cache_dir)

    # Inicializar exportador
    export_dir = config.get("app", {}).get("export_dir", "exports")
    exporter = DocumentExporter(export_dir=export_dir)

    return config, logger, cache, exporter


def init_session_state():
    """Inicializa variables de estado de Streamlit."""
    if "documents" not in st.session_state:
        st.session_state.documents: List[Document] = []
    if "selected_ids" not in st.session_state:
        st.session_state.selected_ids: Dict[str, bool] = {}
    if "translations_started" not in st.session_state:
        st.session_state.translations_started = False
    if "translated_docs" not in st.session_state:
        st.session_state.translated_docs: List[Document] = []
    if "exported_files" not in st.session_state:
        st.session_state.exported_files: Dict[str, Path] = {}
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False  # Modo claro por defecto


# =============================================================================
# Funciones auxiliares
# =============================================================================
def create_document_from_uploaded_file(uploaded_file) -> Optional[Document]:
    """Crea un objeto Document desde un archivo subido por Streamlit."""
    filename = uploaded_file.name
    file_type = FileType.from_extension(filename)

    if file_type is None:
        st.error(f"❌ Formato no soportado: {filename}")
        return None

    content = uploaded_file.read()
    file_size = len(content)

    return Document(
        doc_id=str(uuid.uuid4()),
        filename=filename,
        file_type=file_type,
        file_size_bytes=file_size,
        content=content,
    )


def get_available_providers(config: dict) -> Dict[str, bool]:
    """Verifica qué proveedores están disponibles."""
    result = {}
    for provider in TranslationProvider:
        try:
            translator = TranslatorFactory.create(provider, config)
            result[provider.value] = translator.is_available()
        except Exception:
            result[provider.value] = False
    return result


# =============================================================================
# Main App
# =============================================================================
def main():
    # Inicializar
    init_session_state()
    config, logger, cache, exporter = initialize_app()
    
    # Inyectar estilos con modo actual
    inject_styles(st.session_state.dark_mode)

    # Renderizar encabezado
    render_header()

    # Configuración de la app
    app_cfg = config.get("app", {})
    max_files = app_cfg.get("max_files", 20)
    max_file_size_mb = app_cfg.get("max_file_size_mb", 50)
    translation_cfg = config.get("translation", {})

    # =========================================================================
    # Sidebar: Configuración
    # =========================================================================
    with st.sidebar:
        # Título de la sidebar
        st.markdown("## ⚙️ Configuración")
        
        # Selector de tema (primero para que sea visible)
        render_theme_selector()
        
        st.divider()

        # Selector de proveedor
        available_providers = get_available_providers(config)
        selected_provider_str = render_provider_selector(available_providers, default="gemini")
        selected_provider = TranslationProvider(selected_provider_str)

        st.divider()

        # Parámetros de traducción
        st.subheader("📊 Parámetros")
        chunk_size = st.slider(
            "Tamaño de fragmento (tokens)",
            min_value=1000,
            max_value=8000,
            value=translation_cfg.get("chunk_size_tokens", 3500),
            step=500,
            help="Tamaño máximo de cada fragmento enviado al traductor",
        )

        max_workers = st.slider(
            "⚡ Hilos de procesamiento",
            min_value=1,
            max_value=8,
            value=translation_cfg.get("max_workers", 4),
            step=1,
            help="Número de traducciones simultáneas",
        )

        st.divider()

        # Estadísticas de caché
        render_cache_stats(cache.stats())

        if st.button("🗑️ Limpiar caché", type="secondary", use_container_width=True):
            cache.clear()
            st.success("✅ Caché limpiada correctamente")
            st.rerun()

        # Información de la aplicación
        st.divider()
        st.caption("📄 Paper Translator v2.0")
        st.caption("🔧 Costo: $0 (usando Gemini Free Tier)")

    # =========================================================================
    # Área principal: Carga de archivos
    # =========================================================================
    st.header("📤 1. Cargar documentos")
    st.markdown("Arrastra y suelta tus archivos para comenzar la traducción.")

    supported_types = ["pdf", "docx", "txt", "tex"]
    
    # Crear contenedor con estilo para upload
    with st.container():
        uploaded_files = st.file_uploader(
            f"📂 Sube hasta {max_files} archivos",
            type=supported_types,
            accept_multiple_files=True,
            help=f"Formatos soportados: PDF, DOCX, TXT, LaTeX (.tex). "
                 f"Tamaño máximo por archivo: {max_file_size_mb} MB",
            label_visibility="collapsed",
        )

    # Procesar archivos subidos
    if uploaded_files:
        # Limitar cantidad
        if len(uploaded_files) > max_files:
            st.warning(
                f"⚠️ Se cargaron {len(uploaded_files)} archivos. "
                f"Solo se procesarán los primeros {max_files}."
            )
            uploaded_files = uploaded_files[:max_files]

        # Crear documentos nuevos (evitar duplicados)
        existing_names = {d.filename for d in st.session_state.documents}
        new_docs = []

        with st.spinner("📥 Procesando archivos..."):
            for uf in uploaded_files:
                if uf.name not in existing_names:
                    doc = create_document_from_uploaded_file(uf)
                    if doc:
                        new_docs.append(doc)
                        st.session_state.selected_ids[doc.doc_id] = True

        if new_docs:
            st.session_state.documents.extend(new_docs)
            st.success(f"✅ Se cargaron {len(new_docs)} archivos nuevos.")
            st.rerun()

    # =========================================================================
    # Tabla de selección
    # =========================================================================
    st.header("📋 2. Seleccionar archivos para traducir")

    if st.session_state.documents:
        # Botones de selección masiva con mejor diseño
        col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
        with col1:
            if st.button("✅ Seleccionar todos", use_container_width=True):
                for doc in st.session_state.documents:
                    st.session_state.selected_ids[doc.doc_id] = True
                st.rerun()
        with col2:
            if st.button("❌ Deseleccionar todos", use_container_width=True):
                for doc in st.session_state.documents:
                    st.session_state.selected_ids[doc.doc_id] = False
                st.rerun()
        with col3:
            # Mostrar contador de seleccionados
            selected_count = sum(1 for d in st.session_state.documents 
                               if st.session_state.selected_ids.get(d.doc_id, False))
            st.markdown(f"**{selected_count}/{len(st.session_state.documents)}** seleccionados")

        # Renderizar tabla
        st.session_state.selected_ids = render_file_table(
            st.session_state.documents,
            st.session_state.selected_ids,
        )

        # Calcular tokens totales seleccionados
        selected_docs = [
            d for d in st.session_state.documents
            if st.session_state.selected_ids.get(d.doc_id, False)
        ]

        if selected_docs:
            # Primero procesar aquellos que no tienen tokens estimados
            with st.spinner("📊 Analizando documentos..."):
                for doc in selected_docs:
                    if doc.estimated_tokens == 0 and doc.status == TranslationStatus.PENDING:
                        try:
                            processor = ProcessorFactory.get_processor(doc.file_type)
                            doc.status = TranslationStatus.LOADING
                            doc = processor.process(doc)
                            doc.status = TranslationStatus.LOADED
                        except Exception as e:
                            doc.status = TranslationStatus.ERROR
                            doc.error_message = str(e)
                            logger.error(f"Error pre-procesando {doc.filename}: {e}")

            total_tokens = sum(d.estimated_tokens for d in selected_docs if d.estimated_tokens)

            # Mostrar estimación de costo (usando FallbackTranslator)
            try:
                translator_for_estimate = FallbackTranslator.create_default(config)
                render_cost_estimate(total_tokens, translator_for_estimate)
            except Exception as e:
                st.warning(f"⚠️ No se pudo calcular estimación de costo: {e}")

            # Botón para iniciar traducción
            st.divider()
            st.header("🚀 3. Iniciar traducción")

            # Verificar que al menos un proveedor esté disponible
            try:
                fallback_translator = FallbackTranslator.create_default(config)
                providers_ready = fallback_translator.translators
                if not providers_ready:
                    st.error(
                        "⚠️ **Ningún proveedor de traducción está configurado.**\n\n"
                        "**Configura al menos uno (gratis):**\n"
                        "1. **Gemini (recomendado, GRATIS)**: Obtén API key en https://aistudio.google.com/apikey\n"
                        "2. **DeepL (fallback gratuito)**: Obtén API key en https://www.deepl.com/pro-api\n\n"
                        "Agrega tus credenciales en `config.yaml` o usa variables de entorno."
                    )
                else:
                    provider_names = [t.get_provider_name() for t in providers_ready]
                    st.info(
                        f"✅ **Proveedores listos en cadena de fallback:**\n\n"
                        f"`{' → '.join(provider_names)}`\n\n"
                        f"🔄 Si el primero falla o se agota, pasará automáticamente al siguiente."
                    )

                    # Botón principal de traducción
                    if st.button(
                        f"🚀 Traducir {len(selected_docs)} documento(s) {'(GRATIS)' if 'gemini' in provider_names else ''}",
                        type="primary",
                        disabled=st.session_state.translations_started,
                        use_container_width=True,
                    ):
                        st.session_state.translations_started = True

                        # Crear pipeline con FallbackTranslator
                        pipeline = TranslationPipeline(
                            config=config,
                            translator=fallback_translator,
                            cache=cache,
                            max_workers=max_workers,
                        )

                        # Contenedores para progreso
                        progress_container = st.container()
                        global_progress_bar = progress_container.progress(0)
                        global_status_text = progress_container.empty()

                        # Callbacks de progreso
                        def doc_progress(progress: TranslationProgress):
                            # Solo logging - la UI se actualiza al final con st.rerun()
                            logger.debug(
                                f"Progreso {progress.filename}: "
                                f"{progress.status.value} - {progress.progress*100:.0f}%"
                            )

                        def global_progress(prog: float, completed: int, total: int):
                            try:
                                global_progress_bar.progress(prog)
                                status_icon = "✅" if prog >= 1.0 else "🔄"
                                global_status_text.text(
                                    f"{status_icon} Progreso global: {completed}/{total} documentos completados "
                                    f"({prog*100:.0f}%)"
                                )
                            except Exception:
                                pass

                        # Ejecutar traducción
                        try:
                            with st.spinner("🔄 Traduciendo documentos..."):
                                translated = pipeline.process_documents_parallel(
                                    selected_docs,
                                    doc_progress_callback=doc_progress,
                                    global_progress_callback=global_progress,
                                )

                            st.session_state.translated_docs = translated
                            st.session_state.translations_started = False

                            success_count = sum(
                                1 for d in translated
                                if d.status in (TranslationStatus.COMPLETED, TranslationStatus.CACHED)
                            )
                            error_count = sum(
                                1 for d in translated if d.status == TranslationStatus.ERROR
                            )

                            if success_count > 0:
                                st.success(f"✅ **{success_count}** documento(s) traducidos exitosamente.")
                            if error_count > 0:
                                st.error(f"❌ **{error_count}** documento(s) tuvieron errores.")

                            # Mostrar info de fallback si se activó
                            if fallback_translator.was_fallback_triggered():
                                fb_info = fallback_translator.get_fallback_info()
                                st.warning(
                                    f"🔄 **Fallback activado:**\n\n"
                                    f"Proveedor activo actual: **{fb_info['active_provider']}**\n\n"
                                    f"Motivo: {fb_info['last_fallback_reason']}"
                                )

                            st.rerun()

                        except Exception as e:
                            st.session_state.translations_started = False
                            st.error(f"❌ Error durante la traducción: {str(e)}")
                            logger.exception("Error en pipeline de traducción")

            except Exception as e:
                st.error(f"❌ Error inicializando sistema de traducción: {e}")
                logger.exception("Error creando FallbackTranslator")

    # =========================================================================
    # 4. Previsualización y exportación
    # =========================================================================
    completed_docs = [
        d for d in st.session_state.documents
        if d.status in (TranslationStatus.COMPLETED, TranslationStatus.CACHED)
    ]

    if completed_docs:
        st.divider()
        st.header("👁️ 4. Previsualizar y exportar")

        # Selector de documento para previsualizar
        doc_options = {d.filename: d for d in completed_docs}
        selected_filename = st.selectbox(
            "Selecciona un documento para previsualizar:",
            list(doc_options.keys()),
            key="preview_selector",
        )

        if selected_filename:
            selected_doc = doc_options[selected_filename]
            render_side_by_side_preview(selected_doc)

        # Exportación
        st.subheader("📥 Exportar traducciones")

        col1, col2 = st.columns([2, 1])
        
        with col1:
            export_format = st.radio(
                "Formato de exportación:",
                ["Formato original", "PDF", "DOCX (estilo académico)", "TXT", "LaTeX"],
                horizontal=True,
                key="export_format",
            )
        
        with col2:
            st.write("")  # Espaciador
            include_all = st.checkbox("📦 Incluir todos los formatos", value=False)

        # Botones de exportación
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📦 Generar descargas individuales", use_container_width=True):
                exported = {}
                formats_to_export = ["pdf", "docx", "txt", "latex"] if include_all else [export_format.lower()]
                
                # Mapeo de formatos
                format_map = {
                    "formato original": "original",
                    "pdf": "pdf",
                    "docx (estilo académico)": "docx",
                    "txt": "txt",
                    "latex": "latex",
                }
                
                for doc in completed_docs:
                    try:
                        fmt = export_format.lower()
                        if fmt == "formato original":
                            path = exporter.export_original_format(doc)
                        elif fmt == "pdf":
                            path = exporter.export_to_pdf(doc)
                        elif fmt == "docx (estilo académico)":
                            path = exporter.export_to_docx(doc)
                        elif fmt == "txt":
                            path = exporter.export_to_txt(doc)
                        elif fmt == "latex":
                            path = exporter.export_to_latex(doc)
                        else:
                            path = exporter.export_original_format(doc)
                        exported[doc.filename] = path
                    except Exception as e:
                        st.error(f"❌ Error exportando {doc.filename}: {e}")

                st.session_state.exported_files = exported

                if exported:
                    st.success(f"✅ Se exportaron {len(exported)} archivos.")

        with col2:
            if st.button("📥 Descargar todo en ZIP", use_container_width=True):
                exported_paths = []
                for doc in completed_docs:
                    try:
                        fmt = export_format.lower()
                        if fmt == "formato original":
                            path = exporter.export_original_format(doc)
                        elif fmt == "pdf":
                            path = exporter.export_to_pdf(doc)
                        elif fmt == "docx (estilo académico)":
                            path = exporter.export_to_docx(doc)
                        elif fmt == "txt":
                            path = exporter.export_to_txt(doc)
                        elif fmt == "latex":
                            path = exporter.export_to_latex(doc)
                        else:
                            path = exporter.export_original_format(doc)
                        exported_paths.append(path)
                    except Exception as e:
                        st.error(f"❌ Error exportando {doc.filename}: {e}")

                if exported_paths:
                    zip_path = exporter.create_zip_bundle(exported_paths)
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar ZIP",
                            data=f.read(),
                            file_name=zip_path.name,
                            mime="application/zip",
                            use_container_width=True,
                        )

        # Mostrar botones de descarga individuales
        if st.session_state.exported_files:
            st.markdown("**📎 Descargas individuales:**")
            
            # Mostrar en grid
            cols = st.columns(3)
            for i, (filename, path) in enumerate(st.session_state.exported_files.items()):
                with cols[i % 3]:
                    if path.exists():
                        with open(path, "rb") as f:
                            st.download_button(
                                label=f"⬇️ {path.name}",
                                data=f.read(),
                                file_name=path.name,
                                key=f"download_{filename}_{i}",
                                use_container_width=True,
                            )

    # =========================================================================
    # Sección de ayuda / información
    # =========================================================================
    with st.expander("ℹ️ Información y ayuda", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🚀 Características principales
            
            - **Formatos soportados**: PDF, DOCX, TXT, LaTeX (.tex)
            - **Múltiples proveedores**: Gemini (gratis), DeepL (gratis), OpenAI
            - **Preservación de formato**: Ecuaciones, tablas, citas
            - **Traducción paralela**: Múltiples documentos simultáneos
            - **Caché inteligente**: Evita reprocesar archivos
            - **Chunking automático**: Maneja documentos largos
            """)
        
        with col2:
            st.markdown("""
            ### 💰 Costos (Q3 2026)
            
            | Proveedor | Costo | Límite gratuito |
            |-----------|-------|-----------------|
            | **Gemini** | 🆓 **$0** | 1M tokens/día |
            | **DeepL** | 🆓 **$0** | 500K chars/mes |
            | **OpenAI** | 💰 Pago | Sin capa gratuita |
            
            🎯 **Recomendado**: Gemini por su generosa capa gratuita.
            """)
        
        st.divider()
        
        st.markdown("""
        ### 🔧 Configuración rápida
        
        1. Copia `config.yaml.example` a `config.yaml`
        2. Agrega tus API keys:
           - `GEMINI_API_KEY` (recomendado, gratis) → https://aistudio.google.com/apikey
           - `DEEPL_API_KEY` (fallback, gratis) → https://www.deepl.com/pro-api
        3. ¡Listo! La app usará Gemini primero y fallback automático a DeepL si es necesario.
        """)
        
        # Badge de estado de la app
        st.caption(f"📄 Paper Translator v2.0 | Modo: {'🌙 Oscuro' if st.session_state.dark_mode else '☀️ Claro'}")


if __name__ == "__main__":
    main()