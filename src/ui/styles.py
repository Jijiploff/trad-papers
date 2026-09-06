# styles.py - Versión con sidebar siempre oscuro

def get_css(dark_mode: bool = False) -> str:
    """Devuelve el CSS personalizado según el modo seleccionado."""
    
    # Colores para el sidebar (SIEMPRE OSCURO)
    sidebar_bg = "#0d1117"  # Fondo oscuro estilo GitHub Dark
    sidebar_text = "#e6edf3"  # Texto claro
    sidebar_secondary = "#8b949e"  # Texto secundario
    sidebar_border = "#21262d"  # Bordes
    sidebar_hover = "#161b22"  # Hover
    sidebar_accent = "#58a6ff"  # Azul para elementos destacados

    if dark_mode:
        # Modo OSCURO (para el contenido principal)
        bg_primary = "#0a0e1a"
        bg_secondary = "#111827"
        bg_card = "#1a2234"
        bg_hover = "#243049"
        bg_header = "linear-gradient(135deg, #0f1724 0%, #1a2a3f 100%)"
        text_primary = "#e5e7eb"
        text_secondary = "#9ca3af"
        text_muted = "#6b7280"
        border_color = "#2d3748"
        shadow = "0 4px 20px rgba(0,0,0,0.5)"
        accent = "#3b82f6"
        accent_hover = "#60a5fa"
        success = "#10b981"
        warning = "#f59e0b"
        danger = "#ef4444"
        info = "#06b6d4"
        badge_success = "rgba(16, 185, 129, 0.2)"
        badge_error = "rgba(239, 68, 68, 0.2)"
        badge_warning = "rgba(245, 158, 11, 0.2)"
        badge_info = "rgba(6, 182, 212, 0.2)"
        badge_secondary = "rgba(107, 114, 128, 0.2)"
        input_bg = "#1a2234"
        input_border = "#2d3748"
        input_text = "#e5e7eb"
        code_bg = "#0f1724"
        scrollbar_track = "#1a2234"
        scrollbar_thumb = "#2d3748"
        scrollbar_thumb_hover = "#3b82f6"
        radio_text = "#e5e7eb"
        button_secondary_text = "#e5e7eb"
    else:
        # Modo CLARO (para el contenido principal)
        bg_primary = "#f8f9fa"
        bg_secondary = "#ffffff"
        bg_card = "#ffffff"
        bg_hover = "#f1f3f5"
        bg_header = "linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)"
        text_primary = "#1a202c"
        text_secondary = "#2d3748"
        text_muted = "#4a5568"
        border_color = "#e2e8f0"
        shadow = "0 4px 20px rgba(0,0,0,0.08)"
        accent = "#2b6cb0"
        accent_hover = "#3182ce"
        success = "#38a169"
        warning = "#d69e2e"
        danger = "#e53e3e"
        info = "#00a3c4"
        badge_success = "rgba(56, 161, 105, 0.15)"
        badge_error = "rgba(229, 62, 62, 0.15)"
        badge_warning = "rgba(214, 158, 46, 0.15)"
        badge_info = "rgba(0, 163, 196, 0.15)"
        badge_secondary = "rgba(113, 128, 150, 0.15)"
        input_bg = "#ffffff"
        input_border = "#d1d5db"
        input_text = "#1a202c"
        code_bg = "#edf2f7"
        scrollbar_track = "#f1f1f1"
        scrollbar_thumb = "#cbd5e0"
        scrollbar_thumb_hover = "#a0aec0"
        radio_text = "#1a202c"
        button_secondary_text = "#1a202c"

    return f"""
    <style>
    /* ===== Reset y base ===== */
    .stApp {{
        background: {bg_primary};
        color: {text_primary};
        transition: background 0.3s ease, color 0.3s ease;
    }}

    .main .block-container {{
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}

    /* ============================================================
       SIDEBAR - SIEMPRE EN MODO OSCURO
       ============================================================ */

    /* Fondo de la sidebar - siempre oscuro */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {sidebar_border} !important;
    }}

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        background: {sidebar_bg} !important;
    }}

    /* Texto de la sidebar - siempre claro */
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] .stMetric label,
    [data-testid="stSidebar"] .stMetric .stMetricValue,
    [data-testid="stSidebar"] .stMetric .stMetricDelta,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label {{
        color: {sidebar_text} !important;
    }}

    /* Texto secundario en sidebar */
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
        color: {sidebar_secondary} !important;
    }}

    /* Divisores en sidebar */
    [data-testid="stSidebar"] hr {{
        border-color: {sidebar_border} !important;
    }}

    /* ===== INPUTS en SIDEBAR ===== */
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stTextArea > div > div > textarea,
    [data-testid="stSidebar"] .stNumberInput > div > div > input,
    [data-testid="stSidebar"] [data-testid="stTextInput"] input,
    [data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
    [data-testid="stSidebar"] [data-testid="stNumberInput"] input {{
        background: {sidebar_bg} !important;
        color: {sidebar_text} !important;
        border-color: {sidebar_border} !important;
        border-radius: 8px !important;
    }}

    /* ===== SELECTBOX en SIDEBAR ===== */
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
        background: {sidebar_bg} !important;
        color: {sidebar_text} !important;
        border-color: {sidebar_border} !important;
    }}

    [data-testid="stSidebar"] .stSelectbox > div > div > div,
    [data-testid="stSidebar"] [data-testid="stSelectbox"] div {{
        color: {sidebar_text} !important;
    }}

    /* ===== RADIO BUTTONS en SIDEBAR ===== */
    [data-testid="stSidebar"] .stRadio > div,
    [data-testid="stSidebar"] [data-testid="stRadio"] {{
        color: {sidebar_text} !important;
    }}

    [data-testid="stSidebar"] .stRadio > div label,
    [data-testid="stSidebar"] .stRadio > div label span,
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label span,
    [data-testid="stSidebar"] [data-testid="stRadio"] label p,
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label,
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {{
        color: {sidebar_text} !important;
    }}

    /* ===== CHECKBOXES en SIDEBAR ===== */
    [data-testid="stSidebar"] .stCheckbox > label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label span,
    [data-testid="stSidebar"] [data-testid="stCheckbox"] label p {{
        color: {sidebar_text} !important;
    }}

    /* ===== SLIDERS en SIDEBAR ===== */
    [data-testid="stSidebar"] .stSlider > div > div,
    [data-testid="stSidebar"] [data-testid="stSlider"] {{
        color: {sidebar_text} !important;
    }}

    [data-testid="stSidebar"] .stSlider label,
    [data-testid="stSidebar"] [data-testid="stSlider"] label {{
        color: {sidebar_secondary} !important;
    }}

    /* ===== EXPANDERS en SIDEBAR ===== */
    [data-testid="stSidebar"] .streamlit-expanderHeader,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
        background: {sidebar_bg} !important;
        border-radius: 10px !important;
        border: 1px solid {sidebar_border} !important;
        color: {sidebar_text} !important;
    }}

    [data-testid="stSidebar"] .streamlit-expanderContent,
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: {sidebar_bg} !important;
        border-radius: 0 0 10px 10px !important;
        border: 1px solid {sidebar_border} !important;
        border-top: none !important;
        color: {sidebar_text} !important;
    }}

    /* ===== BOTONES en SIDEBAR ===== */
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] [data-testid="stButton"] button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }}

    /* Botones secundarios en sidebar - fondo oscuro */
    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-secondary"],
    [data-testid="stSidebar"] [data-testid="baseButton-secondary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background: {sidebar_bg} !important;
        color: {sidebar_text} !important;
        border: 1px solid {sidebar_border} !important;
    }}

    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-secondary"] p,
    [data-testid="stSidebar"] [data-testid="baseButton-secondary"] p,
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] p {{
        color: {sidebar_text} !important;
    }}

    /* Botones primarios en sidebar */
    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"],
    [data-testid="stSidebar"] [data-testid="baseButton-primary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] button[kind="primary"] {{
        background: {sidebar_accent} !important;
        color: #ffffff !important;
        border: 1px solid {sidebar_accent} !important;
    }}

    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] p,
    [data-testid="stSidebar"] [data-testid="baseButton-primary"] p,
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p {{
        color: #ffffff !important;
    }}

    /* ===== MÉTRICAS en SIDEBAR ===== */
    [data-testid="stSidebar"] .stMetric,
    [data-testid="stSidebar"] [data-testid="stMetric"] {{
        background: {sidebar_bg};
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid {sidebar_border};
        transition: all 0.2s ease;
        color: {sidebar_text};
    }}

    [data-testid="stSidebar"] .stMetric:hover,
    [data-testid="stSidebar"] [data-testid="stMetric"]:hover {{
        background: {sidebar_hover};
    }}

    [data-testid="stSidebar"] .stMetric label,
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {{
        color: {sidebar_secondary} !important;
        font-weight: 500 !important;
    }}

    [data-testid="stSidebar"] .stMetric .stMetricValue,
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {{
        color: {sidebar_text} !important;
        font-weight: 700 !important;
    }}

    /* ===== TARJETAS DE ESTADO en SIDEBAR ===== */
    [data-testid="stSidebar"] .status-card {{
        background: {sidebar_bg};
        border-left: 4px solid {sidebar_accent};
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 1px solid {sidebar_border};
        color: {sidebar_text};
    }}

    [data-testid="stSidebar"] .status-card.success {{
        border-left-color: #3fb950;
        background: #0d1f14;
    }}

    [data-testid="stSidebar"] .status-card.error {{
        border-left-color: #f85149;
        background: #1f0d0d;
    }}

    [data-testid="stSidebar"] .status-card.warning {{
        border-left-color: #d29922;
        background: #1f1a0d;
    }}

    [data-testid="stSidebar"] .status-card.info {{
        border-left-color: {sidebar_accent};
        background: #0d1a2b;
    }}

    /* ===== BADGES en SIDEBAR ===== */
    [data-testid="stSidebar"] .badge {{
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }}

    /* ===== SCROLLBAR de SIDEBAR ===== */
    [data-testid="stSidebar"]::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}

    [data-testid="stSidebar"]::-webkit-scrollbar-track {{
        background: {sidebar_bg};
        border-radius: 4px;
    }}

    [data-testid="stSidebar"]::-webkit-scrollbar-thumb {{
        background: {sidebar_border};
        border-radius: 4px;
        transition: background 0.2s ease;
    }}

    [data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {{
        background: {sidebar_accent};
    }}

    /* ============================================================
       FIN SIDEBAR - SIEMPRE EN MODO OSCURO
       ============================================================ */

    /* ===== Header ===== */
    .app-header {{
        background: {bg_header};
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: {shadow};
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
    }}

    .app-header::after {{
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 300px;
        height: 300px;
        background: rgba(255,255,255,0.05);
        border-radius: 50%;
        pointer-events: none;
    }}

    .app-header h1 {{
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        position: relative;
        z-index: 1;
    }}

    .app-header p {{
        color: rgba(255,255,255,0.85) !important;
        margin: 0.25rem 0 0 0;
        font-size: 0.95rem;
        position: relative;
        z-index: 1;
        font-weight: 300;
    }}

    /* ===== Tarjetas ===== */
    .status-card {{
        background: {bg_card};
        border-left: 4px solid {accent};
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: {shadow};
        transition: all 0.2s ease;
        color: {text_primary};
    }}

    .status-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}

    .status-card.success {{
        border-left-color: {success};
        background: {badge_success if dark_mode else '#f0fff4'};
    }}

    .status-card.error {{
        border-left-color: {danger};
        background: {badge_error if dark_mode else '#fff5f5'};
    }}

    .status-card.warning {{
        border-left-color: {warning};
        background: {badge_warning if dark_mode else '#fffbf0'};
    }}

    .status-card.info {{
        border-left-color: {info};
        background: {badge_info if dark_mode else '#f0f9ff'};
    }}

    /* ===== Badges ===== */
    .badge {{
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }}

    .badge-success {{
        background: {badge_success};
        color: {success} !important;
        border: 1px solid {success}33;
    }}

    .badge-error {{
        background: {badge_error};
        color: {danger} !important;
        border: 1px solid {danger}33;
    }}

    .badge-warning {{
        background: {badge_warning};
        color: {warning} !important;
        border: 1px solid {warning}33;
    }}

    .badge-info {{
        background: {badge_info};
        color: {info} !important;
        border: 1px solid {info}33;
    }}

    .badge-secondary {{
        background: {badge_secondary};
        color: {text_secondary} !important;
        border: 1px solid {border_color};
    }}


    /* ============================================================
       FIX: TEXTO EN EL ÁREA PRINCIPAL (tabla de archivos, checkboxes,
       st.text, radios, etc.)
       El div "file-table-container" NO envuelve realmente estos
       elementos en el DOM (Streamlit los renderiza como hermanos,
       no como hijos), así que las reglas de arriba nunca aplican y
       el texto queda con el color por defecto del tema (blanco).
       Estas reglas apuntan directo al contenedor principal
       (stMain / .main), que nunca incluye la sidebar, así que no
       rompen el "sidebar siempre oscuro".
       ============================================================ */
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMain"] [data-testid="stText"],
    [data-testid="stMain"] [data-testid="stText"] *,
    [data-testid="stMain"] [data-testid="stCheckbox"] label,
    [data-testid="stMain"] [data-testid="stCheckbox"] label span,
    [data-testid="stMain"] [data-testid="stCheckbox"] label p,
    [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
    [data-testid="stMain"] [data-testid="stWidgetLabel"] label,
    [data-testid="stMain"] [data-testid="stCaptionContainer"] p,
    .main [data-testid="stMarkdownContainer"] p,
    .main [data-testid="stMarkdownContainer"] li,
    .main [data-testid="stMarkdownContainer"] span,
    .main [data-testid="stText"],
    .main [data-testid="stText"] *,
    .main [data-testid="stCheckbox"] label,
    .main [data-testid="stCheckbox"] label span,
    .main [data-testid="stWidgetLabel"] p,
    .main [data-testid="stWidgetLabel"] label {{
        color: {text_primary} !important;
    }}

    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .app-header h1,
    .main [data-testid="stMarkdownContainer"] .app-header h1,
    .app-header h1 {{
        color: #ffffff !important;
    }}

    [data-testid="stMain"] [data-testid="stMarkdownContainer"] .app-header p,
    .main [data-testid="stMarkdownContainer"] .app-header p,
    .app-header p {{
        color: rgba(255, 255, 255, 0.85) !important;
    }}

    /* ===== Panel side-by-side (previsualización) ===== */
    .diff-panel {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        overflow-y: auto;
        box-shadow: {shadow};
        transition: all 0.2s ease;
        color: {text_primary};
        display: flex;
        flex-direction: column;
    }}

    .diff-panel:hover {{
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }}

    .diff-panel h4 {{
        margin: 0 0 0.5rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {border_color};
        color: {text_secondary};
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        flex-shrink: 0;
    }}

    .diff-panel.original h4 {{
        border-bottom-color: {accent};
        color: {accent} !important;
    }}

    .diff-panel.translated h4 {{
        border-bottom-color: {success};
        color: {success} !important;
    }}

    .diff-content {{
        font-size: 0.85rem;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
        color: {text_primary};
        flex: 1;
    }}

    .diff-truncated-note {{
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: {text_muted};
        flex-shrink: 0;
    }}

    /* ===== Navegación de secciones ===== */
    .section-nav {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
        margin-bottom: 0.75rem;
        padding: 0.5rem;
        background: {bg_card};
        border-radius: 10px;
        box-shadow: {shadow};
    }}

    /* ===== INPUTS en CONTENIDO PRINCIPAL ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border-color: {input_border} !important;
        border-radius: 8px !important;
    }}

    /* ===== SELECTBOX en CONTENIDO PRINCIPAL ===== */
    .stSelectbox > div > div,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border-color: {input_border} !important;
    }}

    .stSelectbox > div > div > div,
    [data-testid="stSelectbox"] div {{
        color: {input_text} !important;
    }}

    /* ===== RADIO BUTTONS en CONTENIDO PRINCIPAL ===== */
    .stRadio > div,
    [data-testid="stRadio"] {{
        color: {radio_text} !important;
    }}

    .stRadio > div label,
    .stRadio > div label span,
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label span,
    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] div[role="radiogroup"] label {{
        color: {radio_text} !important;
    }}

    /* ===== CHECKBOXES ===== */
    .stCheckbox > label,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label span,
    [data-testid="stCheckbox"] label p {{
        color: {text_primary} !important;
    }}

    /* ===== BUTTONS en CONTENIDO PRINCIPAL ===== */
    .stButton > button,
    [data-testid="stButton"] button,
    button[kind="primary"],
    button[kind="secondary"] {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }}

    .stButton > button:hover,
    [data-testid="stButton"] button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    .stButton > button[data-testid="baseButton-primary"],
    [data-testid="baseButton-primary"],
    [data-testid="stBaseButton-primary"],
    button[kind="primary"] {{
        background: {accent} !important;
        color: #ffffff !important;
        border: 1px solid {accent} !important;
    }}

    .stButton > button[data-testid="baseButton-primary"] p,
    [data-testid="baseButton-primary"] p,
    [data-testid="stBaseButton-primary"] p {{
        color: #ffffff !important;
    }}

    .stButton > button[data-testid="baseButton-secondary"],
    [data-testid="baseButton-secondary"],
    [data-testid="stBaseButton-secondary"],
    button[kind="secondary"] {{
        background: {bg_secondary} !important;
        color: {button_secondary_text} !important;
        border: 1px solid {input_border} !important;
    }}

    .stButton > button[data-testid="baseButton-secondary"] p,
    [data-testid="baseButton-secondary"] p,
    [data-testid="stBaseButton-secondary"] p {{
        color: {button_secondary_text} !important;
    }}

    /* ===== MÉTRICAS ===== */
    .stMetric,
    [data-testid="stMetric"] {{
        background: {bg_card};
        padding: 1rem;
        border-radius: 12px;
        box-shadow: {shadow};
        transition: all 0.2s ease;
        color: {text_primary};
    }}

    .stMetric:hover,
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}

    .stMetric label,
    [data-testid="stMetricLabel"] {{
        color: {text_secondary} !important;
        font-weight: 500 !important;
    }}

    .stMetric .stMetricValue,
    [data-testid="stMetricValue"] {{
        color: {text_primary} !important;
        font-weight: 700 !important;
    }}

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {{
        background: {bg_card} !important;
        border-radius: 10px !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
    }}

    .streamlit-expanderContent,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: {bg_card} !important;
        border-radius: 0 0 10px 10px !important;
        border: 1px solid {border_color} !important;
        border-top: none !important;
        color: {text_primary} !important;
    }}

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.25rem;
        background: {bg_card};
        padding: 0.5rem;
        border-radius: 12px;
        box-shadow: {shadow};
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        color: {text_secondary} !important;
        font-weight: 500;
        transition: all 0.2s ease;
        font-size: 0.85rem;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: {bg_hover};
        color: {text_primary} !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: {accent} !important;
        color: white !important;
    }}

    /* ===== CÓDIGO ===== */
    code {{
        background: {code_bg};
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: {text_primary};
    }}

    /* ===== SCROLLBARS ===== */
    .diff-panel::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}

    .diff-panel::-webkit-scrollbar-track {{
        background: {scrollbar_track};
        border-radius: 4px;
    }}

    .diff-panel::-webkit-scrollbar-thumb {{
        background: {scrollbar_thumb};
        border-radius: 4px;
        transition: background 0.2s ease;
    }}

    .diff-panel::-webkit-scrollbar-thumb:hover {{
        background: {scrollbar_thumb_hover};
    }}

    /* ===== OCULTAR ELEMENTOS ===== */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* ===== ANIMACIONES ===== */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .app-header,
    .status-card,
    .diff-panel {{
        animation: fadeIn 0.5s ease forwards;
    }}

    /* ===== RESPONSIVE ===== */
    @media (max-width: 640px) {{
        .app-header {{
            padding: 1rem;
        }}
        .app-header h1 {{
            font-size: 1.3rem;
        }}
        .file-table-container {{
            padding: 0.5rem;
        }}
        .diff-panel {{
            height: 250px !important;
            padding: 0.75rem;
        }}
        .section-nav {{
            gap: 0.2rem;
            padding: 0.3rem;
        }}
    }}

    /* ===== METRICAS DE CACHÉ ===== */
    .stMetric .stMetricDelta,
    [data-testid="stMetricDelta"] {{
        color: {text_muted} !important;
    }}

    /* ===== SLIDERS en CONTENIDO PRINCIPAL ===== */
    .stSlider > div > div,
    [data-testid="stSlider"] {{
        color: {text_primary} !important;
    }}

    .stSlider label,
    [data-testid="stSlider"] label {{
        color: {text_secondary} !important;
    }}

    /* ===== INFO BOXES ===== */
    .stAlert {{
        color: {text_primary} !important;
    }}

    .stAlert > div {{
        color: {text_primary} !important;
    }}

    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {{
        color: inherit !important;
    }}

    /* ============================================================
       Elementos de la SIDEBAR que necesitan override adicional
       (van al final para ganar siempre la cascada frente a las
       reglas generales de arriba)
       ============================================================ */

    /* Sidebar - todos los elementos dentro de la sidebar */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stImage"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
        color: {sidebar_text} !important;
    }}

    /* Sidebar - todos los textos dentro de la sidebar */
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption p {{
        color: {sidebar_text} !important;
    }}

    /* Sidebar - excepción para los botones primarios que deben ser blancos */
    [data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] *,
    [data-testid="stSidebar"] [data-testid="baseButton-primary"] *,
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] *,
    [data-testid="stSidebar"] button[kind="primary"] * {{
        color: #ffffff !important;
    }}
    </style>
    """