# Paper Translator

> Aplicación web para la traducción masiva de papers científicos del inglés al español, con preservación de formato académico.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Características

- 📄 **Formatos soportados**: PDF, DOCX, TXT, LaTeX (.tex)
- 🚀 **Traducción paralela**: Procesamiento simultáneo de hasta 20 archivos
- 🤖 **Múltiples proveedores**: OpenAI GPT-4o, DeepL API, modelos locales vía Ollama
- 🧮 **Preservación de formato**: Ecuaciones matemáticas, tablas, citas, referencias cruzadas
- 🔄 **Chunking inteligente**: Manejo automático de documentos largos (>4000 tokens)
- 💾 **Caché de traducciones**: Evita re-procesar archivos idénticos
- 👀 **Previsualización lado a lado**: Comparación original vs. traducción con navegación por secciones
- 📦 **Exportación flexible**: Formato original, DOCX académico, TXT, LaTeX o ZIP consolidado

## Estructura del proyecto

```
paper-translator/
├── app.py                      # Aplicación principal Streamlit
├── requirements.txt            # Dependencias
├── config.yaml.example         # Plantilla de configuración
├── README.md                   # Este archivo
├── cache/                      # Caché de traducciones (auto-creado)
├── logs/                       # Archivos de log (auto-creado)
├── exports/                    # Archivos exportados (auto-creado)
└── src/
    ├── __init__.py
    ├── core/                   # Modelos y lógica central
    │   ├── __init__.py
    │   ├── models.py           # Dataclasses: Document, Section, Chunk
    │   └── pipeline.py         # Orquestación del proceso de traducción
    ├── processors/             # Procesadores de archivos
    │   ├── __init__.py
    │   ├── base.py             # Clase base abstracta
    │   ├── pdf_processor.py    # Extracción de texto desde PDF
    │   ├── docx_processor.py   # Extracción desde DOCX
    │   ├── txt_processor.py    # Procesamiento de texto plano
    │   └── latex_processor.py  # Parsing de archivos LaTeX
    ├── translators/            # Motores de traducción
    │   ├── __init__.py
    │   ├── base.py             # Interfaz abstracta + reintentos/rate limit
    │   ├── openai_translator.py
    │   ├── deepl_translator.py
    │   └── ollama_translator.py
    ├── utils/                  # Utilidades
    │   ├── __init__.py
    │   ├── config.py           # Carga de configuración
    │   ├── logger.py           # Configuración de logging
    │   ├── chunker.py          # Algoritmo de chunking inteligente
    │   ├── cache.py            # Sistema de caché en disco
    │   └── exporter.py         # Exportación a múltiples formatos
    └── ui/                     # Componentes de interfaz
        ├── __init__.py
        ├── styles.py           # CSS personalizado
        └── components.py       # Componentes Streamlit reutilizables
```

## Instalación

### Requisitos previos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)

### Pasos

```bash
# 1. Clonar o descargar el proyecto
cd paper-translator

# 2. (Opcional pero recomendado) Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar credenciales
cp config.yaml.example config.yaml
# Edita config.yaml con tus API keys
```

### Configuración de credenciales

Edita `config.yaml` y agrega tus credenciales:

```yaml
providers:
  openai:
    api_key: "tu-api-key-openai"
  deepl:
    api_key: "tu-api-key-deepl"
```

Alternativamente, usa variables de entorno:

```bash
export OPENAI_API_KEY="tu-api-key"
export DEEPL_API_KEY="tu-api-key"
```

### Uso de Ollama (modelos locales)

```bash
# Instalar Ollama: https://ollama.ai/
# Descargar modelo
ollama pull llama3.1

# La app detectará automáticamente Ollama en http://localhost:11434
```

## Ejecución

### Local

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

### Streamlit Cloud

1. Sube el proyecto a un repositorio GitHub (público o privado)
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. Configura las variables de entorno en **Settings > Secrets**:
   ```
   OPENAI_API_KEY=tu-api-key
   DEEPL_API_KEY=tu-api-key
   ```
5. Despliega 🚀

> **Nota**: Ollama no está disponible en Streamlit Cloud (requiere servicio local). Usa OpenAI o DeepL para despliegues en la nube.

## Guía de uso

1. **Cargar archivos**: Arrastra y suelta hasta 20 archivos en el área designada
2. **Seleccionar**: Marca los documentos que deseas traducir en la tabla
3. **Configurar**: Elige proveedor de traducción y parámetros en la barra lateral
4. **Traducir**: Haz clic en "Traducir" y monitorea el progreso
5. **Previsualizar**: Usa el panel lado a lado para revisar las traducciones
6. **Exportar**: Descarga archivos individuales o un paquete ZIP consolidado

## Consideraciones de costo por proveedor

### OpenAI GPT-4o (Q3 2026)

| Tipo | Costo por 1M tokens | Ejemplo: 10K tokens |
|------|---------------------|---------------------|
| Entrada | $5.00 | $0.05 |
| Salida | $15.00 | $0.15 |
| **Total aprox.** | **~$20.00** | **~$0.20** |

- Paper promedio (~8,000 palabras / ~10K tokens): **~$0.20 USD**
- 20 papers completos: **~$4.00 USD**

> 💡 **Alternativa económica**: Usa `gpt-4o-mini` ($0.15 / 1M entrada, $0.60 / 1M salida) para bajar costos ~90% con calidad muy buena.

### DeepL API (Q3 2026)

| Plan | Costo | Límite |
|------|-------|--------|
| **Free** | $0.00 | 500,000 caracteres/mes (~125K tokens) |
| **Pro** | $4.99/mes + $0.00002/carácter | Sin límite |

- Paper promedio (~40,000 caracteres): **~$0.80 USD** (Pro) o gratis dentro del límite
- 20 papers (~800K caracteres): Supera límite gratuito, costo Pro ~$16.00 + cuota mensual

### Ollama (Modelos locales)

| Concepto | Costo | Notas |
|----------|-------|-------|
| Por uso | **$0.00** | Sin costo por tokens |
| Hardware | Variable | GPU recomendada para buena velocidad |
| Electricidad | Mínima | Depende del sistema |

- **Llama 3.1 8B**: Funciona bien en CPU, más rápido con GPU de 8GB+ VRAM
- **Llama 3.1 70B**: Requiere GPU de alta gama (24GB+ VRAM) o CPU muy potente
- Privacidad total: los documentos nunca salen de tu máquina

### Resumen comparativo

| Criterio | OpenAI GPT-4o | DeepL | Ollama |
|----------|---------------|-------|--------|
| **Calidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Costo** | Medio | Bajo/Gratis | **Cero** |
| **Velocidad** | Muy rápida | Rápida | Depende de hardware |
| **Privacidad** | API externa | API externa | **Total (local)** |
| **Configuración** | API key | API key | Instalar Ollama + modelo |

## Arquitectura

### Principios de diseño

- **Modularidad**: Separación clara de responsabilidades (UI, procesadores, traductores, utilidades)
- **Extensibilidad**: Fácil agregar nuevos proveedores o formatos de archivo
- **Robustez**: Manejo de errores, reintentos con backoff exponencial, rate limiting
- **Rendimiento**: Procesamiento paralelo con `ThreadPoolExecutor`
- **Eficiencia**: Caché SHA-256 para evitar traducciones redundantes

### Flujo de procesamiento

```
Archivo subido
    ↓
ProcessorFactory → Procesador específico (PDF/DOCX/TXT/LaTeX)
    ↓
Extraer texto + Detectar secciones
    ↓
Chunker → Fragmentos inteligentes (preserva ecuaciones/citas)
    ↓
¿En caché? → Sí → Recuperar traducción
    ↓ No
TranslatorFactory → Proveedor seleccionado
    ↓
Traducción paralela de chunks (ThreadPoolExecutor)
    ↓
Ensamblar secciones traducidas
    ↓
Guardar en caché
    ↓
Previsualizar / Exportar
```

## Manejo de errores

La aplicación maneja robustamente:

- **Archivos corruptos**: Detección y mensaje claro al usuario
- **PDFs protegidos**: Detecta contraseñas y solicita versión sin protección
- **APIs caídas**: Reintentos automáticos con backoff exponencial
- **Timeouts**: Límite configurable por solicitud
- **Rate limits**: Pausas automáticas y reintentos
- **Problemas de autenticación**: Detección temprana y guía de configuración

## Personalización

### Agregar un nuevo proveedor de traducción

1. Crea una clase en `src/translators/` que herede de `BaseTranslator`
2. Implementa `translate_text()`, `get_provider_name()`, `is_available()`
3. Regístrala en `TranslatorFactory.create()` en `src/translators/__init__.py`

### Agregar un nuevo formato de archivo

1. Crea una clase en `src/processors/` que herede de `BaseFileProcessor`
2. Implementa `can_handle()`, `extract_text()`, `get_page_count()`
3. Regístrala en `ProcessorFactory._processors`

## Logging

Los logs se almacenan en `logs/app.log` con el siguiente formato:

```
2026-09-02 10:30:45 | INFO     | paper_translator | pipeline.py:120 | Documento paper.pdf: 12 chunks para traducir
```

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

MIT License - ver archivo LICENSE para detalles.

---

**Hecho con ❤️ para la comunidad académica hispanohablante**
