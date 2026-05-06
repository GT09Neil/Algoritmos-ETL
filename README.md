# AlgoFinance — Dashboard Bursátil

> Proyecto del curso **Análisis de Algoritmos 2026-1** — Universidad del Quindío.

Dashboard web para análisis financiero de 20 activos bursátiles, con algoritmos
de similitud, detección de patrones y clasificación de riesgo implementados
manualmente (sin librerías de alto nivel).

---

## Requisitos

- **Python 3.10+**
- Conexión a Internet (para el ETL — descarga datos de Yahoo Finance)

## Instalación

```bash
# Clonar el repositorio
git clone <url-del-repo>
cd Algoritmos-ETL

# Instalar dependencias
pip install -r requirements.txt
```

Las únicas dependencias son:
- `flask` — servidor web
- `reportlab` — generación de PDF
- `waitress` — servidor WSGI para producción (Windows)

## Ejecución

### 1. Ejecutar el ETL (descarga y procesa datos)

```bash
python main.py
```

Esto descarga datos OHLCV de 20 activos (7 años de historia) desde la API de
Yahoo Finance, limpia y unifica los datos, y genera `data/dataset_maestro.csv`.

> **Nota:** La primera ejecución puede tardar ~2-3 minutos por el rate limiting
> de la API. Las ejecuciones posteriores son más rápidas si se mantiene el CSV.

### 2. Iniciar el dashboard web

```bash
python app.py
```

Abrir en el navegador: **http://localhost:5000**

### 3. Exportar reporte PDF

Desde el dashboard, hacer clic en el botón **"Exportar PDF"** en la barra superior.
También se puede generar directamente:

```bash
python -m visualization.pdf_export
```

El PDF se guarda en `data/reporte_bursatil.pdf`.

---

## Estructura del Proyecto

```
Algoritmos-ETL/
├── app.py                          # Servidor Flask (dashboard web)
├── main.py                         # CLI: ETL + benchmarks de ordenamiento
├── config.py                       # Constantes globales
├── requirements.txt                # Dependencias (flask, reportlab, waitress)
│
├── etl/                            # Pipeline ETL
│   ├── data_fetcher.py             # Descarga HTTP directa (Yahoo Chart API v8)
│   ├── data_cleaner.py             # Limpieza: forward fill, detección anomalías
│   ├── data_unifier.py             # Calendario maestro, alineación, unificación
│   └── etl_pipeline.py             # Orquestador del ETL
│
├── algorithms/                     # Algoritmos implementados manualmente
│   ├── sorting.py                  # 12 algoritmos de ordenamiento
│   ├── similarity.py               # 4 algoritmos de similitud (R2)
│   ├── patterns.py                 # Sliding window: detección de patrones (R3)
│   ├── volatility.py               # Volatilidad + clasificación de riesgo (R3)
│   └── technical.py                # Retornos, SMA, media, desv. estándar
│
├── visualization/                  # Exportación
│   └── pdf_export.py               # Generación de PDF con ReportLab
│
├── benchmarks/                     # Benchmarks de rendimiento
│   └── timing.py                   # Medición de tiempos
│
├── static/                         # Frontend
│   ├── css/style.css               # Dark theme financiero
│   └── js/dashboard.js             # Gráficos Canvas (heatmap, velas, barras)
│
├── templates/                      # HTML (Jinja2)
│   ├── base.html                   # Layout con sidebar
│   ├── dashboard.html              # Página principal
│   ├── similarity.html             # Comparación de similitud
│   ├── patterns.html               # Patrones detectados
│   └── risk.html                   # Clasificación de riesgo
│
├── data/                           # Datos generados
│   ├── dataset_maestro.csv         # Dataset OHLCV (generado por ETL)
│   └── reporte_bursatil.pdf        # Reporte PDF (generado)
│
└── docs/
    └── arquitectura.md             # Documento de diseño
```

---

## Algoritmos Implementados

### Similitud entre series de tiempo (Requerimiento 2)

| Algoritmo | Complejidad Temporal | Complejidad Espacial | Archivo |
|-----------|---------------------|---------------------|---------|
| Distancia Euclidiana | O(n) | O(1) | `similarity.py` |
| Correlación de Pearson | O(n) | O(1) | `similarity.py` |
| Dynamic Time Warping (DTW) | O(n·w) | O(m) | `similarity.py` |
| Similitud por Coseno | O(n) | O(1) | `similarity.py` |

### Detección de patrones (Requerimiento 3)

| Algoritmo | Complejidad Temporal | Archivo |
|-----------|---------------------|---------|
| Días consecutivos al alza (sliding window) | O(n·w) | `patterns.py` |
| Gap-up (acumulador deslizante) | O(n) | `patterns.py` |
| Volatilidad histórica anualizada | O(n) | `volatility.py` |
| Clasificación de riesgo (percentiles) | O(k²) | `volatility.py` |

### Análisis técnico (soporte)

| Función | Complejidad | Archivo |
|---------|------------|---------|
| Retornos logarítmicos | O(n) | `technical.py` |
| Media móvil simple (SMA) | O(n) | `technical.py` |
| Media aritmética | O(n) | `technical.py` |
| Desviación estándar | O(n) | `technical.py` |

### Ordenamiento (soporte)

12 algoritmos en `sorting.py`: BubbleSort, SelectionSort, InsertionSort,
MergeSort, QuickSort, HeapSort, ShellSort, CountingSort, RadixSort,
BucketSort, TimSort, PigeonholeSort.

---

## Restricciones Académicas

| Restricción | Cumplimiento |
|-------------|-------------|
| Sin `yfinance` | ✅ Usa `urllib.request` directo |
| Sin `pandas` / `pandas_datareader` | ✅ Usa `csv` + `dict`/`list` |
| Sin `numpy` / `scipy` / `sklearn` | ✅ Solo `math` estándar |
| Sin `plotly` / `bokeh` / `Chart.js` | ✅ Canvas API nativo |
| Sin datasets estáticos | ✅ ETL descarga en cada ejecución |
| Algoritmos implementados manualmente | ✅ Todos con análisis formal |

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Flask (Python) |
| Frontend | HTML5 + CSS3 + JavaScript vanilla |
| Gráficos | Canvas API del navegador |
| PDF | ReportLab |
| Datos | CSV + dict/list nativos |
| HTTP | urllib.request |

---

## Créditos

- **Curso:** Análisis de Algoritmos — Universidad del Quindío, 2026-1
- **Datos:** Yahoo Finance Chart API v8
- **Activos:** 20 ETFs y ADRs (VOO, SPY, QQQ, EC, CIB, AVAL, PBR, etc.)
