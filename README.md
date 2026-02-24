# Files Gestor

CLI para limpiar y organizar archivos recuperados con TestDisk. Los archivos recuperados vienen en carpetas `recup_dir.*` completamente desorganizados: duplicados por todos lados, basura de WhatsApp mezclada con fotos personales, metadatos faltantes. Este proyecto implementa un pipeline secuencial para convertir ese caos en una biblioteca ordenada de fotos, videos y documentos.

## Instalación

```bash
pip install -r requirements.txt
```

**Dependencias del sistema:**
- `tesseract-ocr` — requerido para `classify-text-images` (`sudo apt install tesseract-ocr`)
- `ffmpeg` / `ffprobe` — requerido para `purge-short-videos` y `organize`

## Uso general

```bash
python -m src.cli <comando> --root /ruta/a/testdisk-recovery/ [opciones]
```

Todos los comandos son **dry-run por defecto**. Usar `--apply` para ejecutar cambios reales. Al aplicar cambios destructivos, se pide confirmación con texto.

---

## Comandos

### `purge-by-type`

Elimina archivos con extensiones no permitidas. Mantiene solo una whitelist de tipos conocidos (imágenes, videos, documentos).

```bash
python -m src.cli purge-by-type --root /ruta/recovery [--apply] [--recup-prefix PREFIX] [--noext-delete-below-mb MB]
```

| Opción | Default | Descripción |
|---|---|---|
| `--apply` | dry-run | Ejecutar borrado real |
| `--recup-prefix` | `recup_dir` | Prefijo de carpetas a procesar |
| `--noext-delete-below-mb` | `1.0` | Borrar archivos sin extensión menores a este tamaño (MB) |

**Extensiones permitidas:** `.jpg .jpeg .png .webp .bmp .heic .heif .mp4 .mov .mkv .avi .3gp .mts .m4v .wmv .pdf .docx .pptx`

---

### `purge-small-images`

Elimina imágenes pequeñas (iconos, thumbnails, avatares) o con aspect ratio extremo (banners, barras de UI).

```bash
python -m src.cli purge-small-images --root /ruta/recovery [--apply] [--min-width PX] [--min-height PX] [--max-aspect-ratio RATIO]
```

| Opción | Default | Descripción |
|---|---|---|
| `--min-width` | `200` | Ancho mínimo en píxeles |
| `--min-height` | `200` | Alto mínimo en píxeles |
| `--max-aspect-ratio` | `5.0` | Aspect ratio máximo permitido |

---

### `purge-short-videos`

Elimina videos cortos (< 5 seg) o pequeños (< 500 KB), típicos estados de WhatsApp y clips basura. Usa `ffprobe` para extraer duración.

```bash
python -m src.cli purge-short-videos --root /ruta/recovery [--apply] [--min-duration SEG] [--min-size-kb KB]
```

| Opción | Default | Descripción |
|---|---|---|
| `--min-duration` | `5.0` | Duración mínima en segundos |
| `--min-size-kb` | `500` | Tamaño mínimo en KB |

---

### `deduplicate`

Elimina duplicados exactos (byte a byte) usando SHA-256. Conserva el primer archivo encontrado, borra el resto. Pre-filtra por tamaño antes de hashear para mayor eficiencia.

```bash
python -m src.cli deduplicate --root /ruta/recovery [--apply]
```

---

### `purge-similar-images`

Elimina imágenes visualmente similares usando pHash (hash perceptual). Diseñado para el caso principal: WhatsApp recomprime fotos, por lo que la misma imagen existe en alta calidad (original) y baja calidad. Conserva la de mayor tamaño en cada grupo.

```bash
python -m src.cli purge-similar-images --root /ruta/recovery [--apply] [--max-distance DIST] [--fuzzy-cap N]
```

| Opción | Default | Descripción |
|---|---|---|
| `--max-distance` | `10` | Distancia Hamming máxima (0=exacto, 10=WhatsApp, 64=cualquiera) |
| `--fuzzy-cap` | `5000` | Límite para la fase O(n²) de comparación fuzzy |

**Algoritmo:** Fase 1 exacta por bucket pHash (O(n)), seguida de fase fuzzy con Union-Find solo para singletons, acotada por `--fuzzy-cap` para evitar timeouts en datasets grandes.

---

### `organize`

Copia (o mueve) archivos desde `recup_dir.*` a una estructura de carpetas organizada por tipo y fecha. Extrae fechas EXIF de fotos y metadatos de videos via ffprobe.

```bash
python -m src.cli organize --root /ruta/recovery --output-dir /ruta/destino [--apply] [--move]
```

| Opción | Default | Descripción |
|---|---|---|
| `--output-dir` | requerido | Carpeta destino |
| `--move` | copiar | Mover en vez de copiar |

**Estructura de salida:**
```
output_dir/
├── fotos/
│   ├── 2023/
│   │   ├── 01_enero/
│   │   └── 02_febrero/
│   └── sin_fecha/
├── videos/
│   └── 2023/ ...
├── documentos/
└── sin_clasificar/
```

Archivos sin fecha van a `sin_fecha/`. Colisiones de nombres se resuelven con sufijos `_1, _2, ...`

---

### `classify-text-images`

Mueve imágenes con alto contenido de texto (memes, screenshots, fotos de apuntes) a una carpeta de cuarentena. Usa OCR (Tesseract) para medir la cobertura de texto.

```bash
python -m src.cli classify-text-images --root /ruta/recovery --output-dir /ruta/memes [--apply] [--text-threshold UMBRAL]
```

| Opción | Default | Descripción |
|---|---|---|
| `--output-dir` | requerido | Carpeta destino para imágenes con texto |
| `--text-threshold` | `0.30` | Fracción mínima de píxeles con texto [0-1] |

Requiere `tesseract-ocr` instalado en el sistema.

---

### `detect-faces`

Mueve imágenes con caras detectadas a una carpeta de "fotos personales". Usa MediaPipe para detección ML sin entrenamiento adicional.

```bash
python -m src.cli detect-faces --root /ruta/recovery --output-dir /ruta/personales [--apply] [--min-confidence CONF]
```

| Opción | Default | Descripción |
|---|---|---|
| `--output-dir` | requerido | Carpeta destino para fotos con caras |
| `--min-confidence` | `0.5` | Umbral de confianza MediaPipe [0-1] |

---

## Pipeline recomendado

Ejecutar los comandos en este orden para mejores resultados:

```bash
ROOT=/ruta/recovery
OUT=/ruta/output

# 1. Limpiar por tipo
python -m src.cli purge-by-type --root $ROOT --apply

# 2. Limpiar imágenes pequeñas y videos cortos
python -m src.cli purge-small-images --root $ROOT --apply
python -m src.cli purge-short-videos --root $ROOT --apply

# 3. Eliminar duplicados exactos
python -m src.cli deduplicate --root $ROOT --apply

# 4. Eliminar similares visuales (WhatsApp vs original)
python -m src.cli purge-similar-images --root $ROOT --apply

# 5. Organizar en carpetas por fecha
python -m src.cli organize --root $ROOT --output-dir $OUT --apply

# 6. Clasificar memes/screenshots (mueve, no borra)
python -m src.cli classify-text-images --root $OUT --output-dir $OUT/memes --apply

# 7. Separar fotos personales con caras
python -m src.cli detect-faces --root $OUT --output-dir $OUT/personales --apply
```

---

## Arquitectura

```
src/
├── cli.py                  # Entry point, parseo de argumentos
└── files_gestor/
    ├── rules.py            # Dataclasses de configuración y whitelists de extensiones
    ├── scan.py             # Iteración de archivos: list_recup_dirs(), iter_files_in_dir()
    ├── purge.py            # Lógica de purge y deduplicación
    ├── organize.py         # Organización por tipo y fecha
    ├── classify.py         # Detección de texto/memes con OCR
    ├── faces.py            # Detección de caras con MediaPipe
    └── report.py           # Generación de reportes CSV
```

Cada comando genera un reporte CSV con timestamp en `_reports/` con todas las decisiones tomadas (acción, razón, extensión, tamaño, ruta).

---

## Estado del pipeline

| Fase | Comando | Estado |
|---|---|---|
| 1.1 Imágenes por dimensiones | `purge-small-images` | ✅ |
| 1.2 Videos por duración | `purge-short-videos` | ✅ |
| 2.1+2.2 Organización por fecha | `organize` | ✅ |
| 3.1 Deduplicación exacta | `deduplicate` | ✅ |
| 3.2 Deduplicación perceptual | `purge-similar-images` | ✅ |
| 4.1 Detección de texto/memes | `classify-text-images` | ✅ |
| 4.3 Detección de caras | `detect-faces` | ✅ |
| 1.3 Audio | — | pendiente |
| 4.2 Clasificación CLIP/Vision | — | pendiente |
