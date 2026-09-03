# styles.py - Versión corregida con mejor soporte para modo claro

def get_css(dark_mode: bool = False) -> str:
    """Devuelve el CSS personalizado según el modo seleccionado."""
    
    if dark_mode:
        # Modo OSCURO
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
    else:
        # Modo CLARO - TODO fondo blanco y letras negras
        bg_primary = "#f8f9fa"
        bg_secondary = "#ffffff"
        bg_card = "#ffffff"
        bg_hover = "#f1f3f5"
        bg_header = "linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)"
        text_primary = "#1a202c"  # Negro
        text_secondary = "#2d3748"  # Gris oscuro
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
        input_text = "#1a202c"  # Negro en inputs
        code_bg = "#edf2f7"
        scrollbar_track = "#f1f1f1"
        scrollbar_thumb = "#cbd5e0"
        scrollbar_thumb_hover = "#a0aec0"
        radio_text = "#1a202c"  # Negro en radio buttons

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
        color: white;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        position: relative;
        z-index: 1;
    }}

    .app-header p {{
        color: rgba(255,255,255,0.85);
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
        color: {success};
        border: 1px solid {success}33;
    }}

    .badge-error {{
        background: {badge_error};
        color: {danger};
        border: 1px solid {danger}33;
    }}

    .badge-warning {{
        background: {badge_warning};
        color: {warning};
        border: 1px solid {warning}33;
    }}

    .badge-info {{
        background: {badge_info};
        color: {info};
        border: 1px solid {info}33;
    }}

    .badge-secondary {{
        background: {badge_secondary};
        color: {text_secondary};
        border: 1px solid {border_color};
    }}

    /* ===== Tabla de archivos ===== */
    .file-table-container {{
        background: {bg_card};
        border-radius: 12px;
        padding: 1rem;
        box-shadow: {shadow};
        overflow-x: auto;
        color: {text_primary};
    }}

    .file-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }}

    .file-table th {{
        background: {bg_secondary if dark_mode else '#f7fafc'};
        padding: 0.75rem 1rem;
        text-align: left;
        font-weight: 600;
        color: {text_secondary};
        border-bottom: 2px solid {border_color};
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .file-table td {{
        padding: 0.75rem 1rem;
        border-bottom: 1px solid {border_color};
        vertical-align: middle;
        color: {text_primary};
    }}

    .file-table tr:hover {{
        background: {bg_hover};
    }}

    /* ===== Panel side-by-side ===== */
    .diff-panel {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        overflow-y: auto;
        box-shadow: {shadow};
        transition: all 0.2s ease;
        color: {text_primary};
        height: 350px;
    }}

    .diff-panel:hover {{
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }}

    .diff-panel h4 {{
        margin-top: 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {border_color};
        color: {text_secondary};
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .diff-panel.original h4 {{
        border-bottom-color: {accent};
        color: {accent};
    }}

    .diff-panel.translated h4 {{
        border-bottom-color: {success};
        color: {success};
    }}

    .diff-content {{
        font-size: 0.85rem;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
        color: {text_primary};
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

    /* ===== INPUTS - Modo claro con letras negras ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border-color: {input_border} !important;
        border-radius: 8px !important;
    }}

    /* ===== RADIO BUTTONS - Modo claro con letras negras ===== */
    .stRadio > div {{
        color: {radio_text} !important;
    }}

    .stRadio > div label {{
        color: {radio_text} !important;
        font-weight: 500 !important;
    }}

    .stRadio > div label span {{
        color: {radio_text} !important;
    }}

    /* ===== CHECKBOXES ===== */
    .stCheckbox > label {{
        color: {text_primary} !important;
    }}

    /* ===== BUTTONS ===== */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        color: {text_primary} !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    .stButton > button[data-testid="baseButton-primary"] {{
        background: {accent} !important;
        color: white !important;
    }}

    .stButton > button[data-testid="baseButton-secondary"] {{
        background: {bg_secondary} !important;
        color: {text_primary} !important;
        border: 1px solid {border_color} !important;
    }}

    /* ===== MÉTRICAS ===== */
    .stMetric {{
        background: {bg_card};
        padding: 1rem;
        border-radius: 12px;
        box-shadow: {shadow};
        transition: all 0.2s ease;
        color: {text_primary};
    }}

    .stMetric:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }}

    .stMetric label {{
        color: {text_secondary} !important;
        font-weight: 500 !important;
    }}

    .stMetric .stMetricValue {{
        color: {text_primary} !important;
        font-weight: 700 !important;
    }}

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {{
        background: {bg_card} !important;
        border-radius: 10px !important;
        border: 1px solid {border_color} !important;
        color: {text_primary} !important;
    }}

    .streamlit-expanderContent {{
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
        color: {text_secondary};
        font-weight: 500;
        transition: all 0.2s ease;
        font-size: 0.85rem;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: {bg_hover};
        color: {text_primary};
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
            height: 250px;
            padding: 0.75rem;
        }}
        .section-nav {{
            gap: 0.2rem;
            padding: 0.3rem;
        }}
    }}

    /* ===== SELECTBOX ===== */
    .stSelectbox > div > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
    }}

    .stSelectbox > div > div > div {{
        color: {input_text} !important;
    }}

    /* ===== METRICAS DE CACHÉ ===== */
    .stMetric .stMetricDelta {{
        color: {text_muted} !important;
    }}

    /* ===== SLIDERS ===== */
    .stSlider > div > div {{
        color: {text_primary} !important;
    }}

    .stSlider label {{
        color: {text_secondary} !important;
    }}

    /* ===== INFO BOXES ===== */
    .stAlert {{
        color: {text_primary} !important;
    }}

    .stAlert > div {{
        color: {text_primary} !important;
    }}
    </style>
    """