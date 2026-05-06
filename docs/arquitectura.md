# Documento de Arquitectura — AlgoFinance

## 1. Visión General

AlgoFinance es una aplicación web para análisis financiero que implementa
algoritmos de similitud, detección de patrones y clasificación de riesgo
sobre series de tiempo bursátiles. La arquitectura sigue un modelo
cliente-servidor con separación clara entre lógica algorítmica, ETL,
y capa de presentación.

## 2. Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────┐
│                    NAVEGADOR (Cliente)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Dashboard │  │Similitud │  │Patrones  │  │Riesgo    │ │
│  │(heatmap, │  │(2 activos│  │(sliding  │  │(tabla,   │ │
│  │ velas)   │  │ métricas)│  │ window)  │  │ ranking) │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │       │
│       └──────────────┴──────────────┴──────────────┘       │
│                Canvas API (gráficos)                       │
│                fetch() → JSON API                          │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
┌────────────────────────┴─────────────────────────────────┐
│                     FLASK (Servidor)                      │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Rutas (app.py)                     │  │
│  │  GET /           → dashboard.html                   │  │
│  │  GET /similarity → similarity.html                  │  │
│  │  GET /patterns   → patterns.html                    │  │
│  │  GET /risk       → risk.html                        │  │
│  │  GET /api/*      → JSON (datos + cálculos)          │  │
│  │  GET /export/pdf → reporte_bursatil.pdf             │  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────┴───────────────────────────────┐  │
│  │              Módulos Algorítmicos                   │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │similarity.py │  │ patterns.py  │                 │  │
│  │  │• Euclidiana   │  │• Rachas alza │                 │  │
│  │  │• Pearson      │  │• Gap-ups     │                 │  │
│  │  │• DTW          │  │              │                 │  │
│  │  │• Coseno       │  │              │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │volatility.py │  │technical.py  │                 │  │
│  │  │• Vol. histórica│ │• Retornos    │                 │  │
│  │  │• Clasif.riesgo│  │• SMA         │                 │  │
│  │  └──────────────┘  └──────────────┘                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────┴───────────────────────────────┐  │
│  │                Pipeline ETL                          │  │
│  │  data_fetcher → data_cleaner → data_unifier          │  │
│  │  (urllib.request)  (forward fill)  (calendario maestro)│ │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────┴───────────────────────────────┐  │
│  │              Almacenamiento                          │  │
│  │  data/dataset_maestro.csv (OHLCV, ~2.8MB)           │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

## 3. Flujo de Datos

```
Yahoo Finance API ──HTTP──→ data_fetcher.py ──JSON──→ data_cleaner.py
                                                          │
                                                    forward fill
                                                    + validación
                                                          │
                                                          ▼
                                                   data_unifier.py
                                                   (calendario maestro)
                                                          │
                                                          ▼
                                                  dataset_maestro.csv
                                                   (1758 filas × 101 cols)
                                                          │
                                         ┌────────────────┼────────────────┐
                                         ▼                ▼                ▼
                                   similarity.py    patterns.py    volatility.py
                                   (4 métricas)     (2 patrones)   (riesgo)
                                         │                │                │
                                         └────────────────┼────────────────┘
                                                          ▼
                                                      app.py
                                                    (JSON API)
                                                          │
                                              ┌───────────┼───────────┐
                                              ▼           ▼           ▼
                                          dashboard   Canvas API   PDF export
                                          (HTML)      (gráficos)   (ReportLab)
```

## 4. Decisiones de Diseño

### 4.1 Sin librerías de alto nivel
Restricción del curso: todos los algoritmos se implementan con `math`, `list`, `dict`.
No se usa numpy, pandas, scipy, sklearn, plotly, yfinance.

### 4.2 Canvas API para gráficos
Se eligió Canvas API del navegador en lugar de librerías como Plotly o Chart.js
para cumplir con la restricción de no usar librerías que encapsulen la lógica
de visualización. Los gráficos se renderizan pixel a pixel en JavaScript.

### 4.3 Flask como backend
Flask es un micro-framework que no añade abstracciones innecesarias.
La lógica de negocio reside en los módulos de `algorithms/`, no en el framework.

### 4.4 CSV como almacenamiento
Se usa CSV plano en lugar de bases de datos para mantener simplicidad y
reproducibilidad. El dataset completo cabe en memoria (~2.8MB).

### 4.5 DTW con banda de Sakoe-Chiba
DTW tiene complejidad O(n·m) sin optimizar. Con la banda de Sakoe-Chiba
se reduce a O(n·w) donde w << m. Además se usa optimización de espacio
con solo 2 filas de la matriz DP, reduciendo de O(n·m) a O(m).

### 4.6 Dos pasadas para Pearson
La fórmula de una sola pasada para correlación de Pearson sufre de
cancelación catastrófica con valores grandes y varianza pequeña.
Se usan dos pasadas (una para medias, otra para sumas cruzadas)
para estabilidad numérica.

## 5. Endpoints de la API

| Método | Ruta | Parámetros | Respuesta |
|--------|------|-----------|-----------|
| GET | `/api/symbols` | — | `{symbols: [...]}` |
| GET | `/api/similarity` | `a`, `b` | Métricas + series |
| GET | `/api/heatmap` | — | Matriz 20×20 |
| GET | `/api/candlestick/<sym>` | `days` | OHLCV + SMA |
| GET | `/api/patterns/<sym>` | `window` | Rachas + gaps |
| GET | `/api/risk` | — | Rankings + umbrales |
| GET | `/export/pdf` | — | Archivo PDF |

## 6. Complejidades Consolidadas

| Operación | Tiempo | Espacio |
|-----------|--------|---------|
| ETL completo | O(k·n) | O(k·n) |
| Heatmap (k activos) | O(k²·n) | O(k²) |
| Similitud (2 activos) | O(n) + O(n·w) DTW | O(m) |
| Patrones (1 activo) | O(n·w) | O(n) |
| Riesgo (k activos) | O(k·n) | O(k·n) |
| PDF completo | O(k·n) | O(k·n) |

Donde k=20 activos, n≈1758 días, w=banda DTW (~440), m=longitud serie.

---

## 7. Implementación del Requerimiento 1: ETL

### Archivo principal: `etl/data_fetcher.py`

**Proceso de descarga:**
1. Se construye la URL de Yahoo Finance Chart API v8 con los parámetros
   `period1` (timestamp inicio) y `period2` (timestamp fin) e `interval=1d`.
2. Se envía una petición HTTP con `urllib.request.urlopen()`.
3. Se parsea la respuesta JSON manualmente con `json.loads()`.
4. Se extraen los arrays de OHLCV desde `chart.result[0].indicators`.
5. Se combinan con las fechas de `chart.result[0].timestamp`.

**Manejo de errores:** reintentos (3x) con delay exponencial, timeout de 90s,
manejo de HTTP 429 (rate limit).

**Limpieza (`etl/data_cleaner.py`):**
- Forward fill: si `Close` es None, se toma el valor del día anterior.
- Detección de anomalías: High < Low, Close fuera de rango [Low, High].
- Justificación: forward fill preserva la continuidad de las series sin
  introducir valores sintéticos; la alternativa (interpolación lineal)
  asume linealidad entre puntos, lo cual es incorrecto para precios.

**Unificación (`etl/data_unifier.py`):**
- Se construye un calendario maestro: unión de todas las fechas de todos
  los activos, ordenadas cronológicamente (insertion sort manual).
- Cada activo se alinea contra el calendario maestro: O(k·n).
- El dataset resultante tiene 1 fila por fecha y 5 columnas por activo (OHLCV).

### Complejidad del ETL completo
- Descarga: O(k) peticiones HTTP (k=20 activos).
- Limpieza: O(k·n) donde n ≈ 1758 registros por activo.
- Unificación: O(k·n) para alinear + O(N·log N) para ordenar calendario (N = fechas únicas).

---

## 8. Implementación del Requerimiento 2: Algoritmos de Similitud

### Archivo: `algorithms/similarity.py`

Todos los algoritmos reciben dos `list[float]` de retornos logarítmicos
(preprocesados con `technical.py`). Se usan retornos en lugar de precios
crudos para normalizar la escala entre activos de distintas magnitudes.

### 8.1 Distancia Euclidiana

**Fórmula:** `d(x,y) = √(Σ(xᵢ - yᵢ)²)`

**Implementación:** un solo loop acumula la suma de cuadrados de diferencias.
Se aplica `math.sqrt()` al final.

**Estructura de datos:** dos `list[float]` de igual longitud. Acceso O(1) por índice.
Un solo acumulador escalar `sum_sq`.

**Complejidad:** O(n) tiempo, O(1) espacio extra.

### 8.2 Correlación de Pearson

**Fórmula:** `r = Σ((xᵢ-x̄)(yᵢ-ȳ)) / √(Σ(xᵢ-x̄)² · Σ(yᵢ-ȳ)²)`

**Implementación en dos pasadas:**
- Pasada 1: calcular medias x̄, ȳ con acumuladores.
- Pasada 2: acumular sum_xy, sum_x2, sum_y2 con las desviaciones.

**Por qué dos pasadas:** la fórmula de una sola pasada
(`Σ(xᵢyᵢ) - n·x̄·ȳ`) sufre cancelación catastrófica cuando los valores
son grandes (~500 para precios) y la varianza es relativamente pequeña.

**Complejidad:** O(n) tiempo, O(1) espacio extra.

### 8.3 Dynamic Time Warping (DTW)

**Definición recursiva:**
```
DTW[i][j] = |a[i] - b[j]| + min(DTW[i-1][j], DTW[i][j-1], DTW[i-1][j-1])
```

**Optimización 1 — Banda de Sakoe-Chiba:**
Solo se evalúan celdas donde `|i - j| ≤ w`. Esto reduce de O(n·m) a O(n·w).
Para n=m=1758 y w=440, esto es ~4× más rápido que la versión completa.

**Optimización 2 — Espacio O(m):**
En lugar de almacenar toda la matriz n×m, solo se mantienen 2 filas
(`prev_row` y `curr_row`). Al terminar cada fila, se intercambian
las referencias sin copiar datos.

**Complejidad:** O(n·w) tiempo, O(m) espacio.

### 8.4 Similitud por Coseno

**Fórmula:** `cos(θ) = (Σ aᵢbᵢ) / (√(Σ aᵢ²) · √(Σ bᵢ²))`

**Implementación:** un solo loop acumula `dot_product`, `norm_a_sq`, `norm_b_sq`.

**Diferencia con Pearson:** Coseno no centra los datos (no resta la media),
por lo que mide la similitud de dirección del vector completo, no solo
la correlación de las desviaciones.

**Complejidad:** O(n) tiempo, O(1) espacio extra.

---

## 9. Implementación del Requerimiento 3: Patrones y Volatilidad

### Archivo: `algorithms/patterns.py`

### 9.1 Patrón 1: Días consecutivos al alza

**Definición formal:** racha de longitud k si `close[i+j] > close[i+j-1]`
para todo j en {1,...,k}.

**Algoritmo:** se crea un array binario `ups[]` donde `ups[i]=1` si el día
subió. Luego, una ventana de tamaño w recorre el array contando rachas
de 1s consecutivos.

**Salida:** diccionario `{longitud_racha: frecuencia}`.
Ejemplo real VOO: {1: 4463, 2: 2248, 3: 1210, ..., 10: 11}.

### 9.2 Patrón 2: Gap-Up

**Definición formal:** `open[i] > high[i-1]`.

**Significado financiero:** el precio abre por encima del máximo del día
anterior, indicando impulso alcista fuerte (frecuente antes de rallies).

**Optimización:** acumulador deslizante — la suma de gap-ups en la ventana
se actualiza en O(1) por paso (+nuevo, -viejo), dando O(n) total.

### Archivo: `algorithms/volatility.py`

### 9.3 Volatilidad Histórica

**Fórmula:**
```
rᵢ = ln(Pᵢ / Pᵢ₋₁)           (retornos logarítmicos)
σ = √((1/(n-1)) Σ(rᵢ - r̄)²)   (desviación estándar muestral)
σ_anual = σ_diaria × √252      (anualización)
```

El factor √252 convierte la volatilidad diaria a anualizada asumiendo
252 días hábiles por año. Esto permite comparar con benchmarks de la
industria (ej: VOO ~20%, PBR ~49%).

### 9.4 Clasificación de Riesgo

1. Calcular volatilidad anualizada para cada activo: O(k·n).
2. Ordenar activos por volatilidad (insertion sort manual): O(k²).
3. Calcular percentiles p33 y p66 con interpolación lineal.
4. Clasificar: ≤p33 → Conservador, ≤p66 → Moderado, >p66 → Agresivo.

---

## 10. Implementación del Requerimiento 4: Dashboard y Visualización

### Backend: `app.py`

Flask sirve 4 páginas HTML y 7 endpoints JSON. Los cálculos se ejecutan
en el backend; el frontend solo renderiza.

**Caché:** el heatmap y el ranking de riesgo se calculan una vez y se almacenan
en un diccionario en memoria (`_CACHE`). Las consultas posteriores retornan
el resultado cacheado en O(1).

### Frontend: `static/js/dashboard.js`

Todos los gráficos se renderizan con **Canvas API nativa** del navegador:

- **Heatmap:** cuadrícula k×k con escala divergente (rojo → blanco → azul).
  Cada celda se pinta con `ctx.fillRect()` y el color se calcula con
  interpolación lineal basada en el valor de correlación.

- **Candlestick:** para cada día se dibuja un rectángulo (cuerpo: open→close)
  y una línea vertical (mecha: low→high). Verde si close>open, rojo si no.
  Las SMA se superponen como líneas continuas con `ctx.lineTo()`.

- **Barras de riesgo:** barras horizontales proporcionales a la volatilidad,
  coloreadas por categoría de riesgo.

### PDF: `visualization/pdf_export.py`

Se usa ReportLab (librería de bajo nivel para PDF) para generar un documento
de 4 páginas con portada, tablas de riesgo, patrones y algoritmos.
No se usa Matplotlib ni ninguna librería de gráficos.

---

## 11. Implementación del Requerimiento 5: Despliegue

### Ejecución local
```
pip install -r requirements.txt
python main.py          # ETL
python app.py           # Dashboard en http://localhost:5000
```

### Despliegue en la nube
- `Procfile` configurado para Render/Railway.
- `requirements.txt` con versiones mínimas (flask>=3.0, reportlab>=4.0, waitress>=2.1).
- El ETL debe ejecutarse antes del despliegue para generar el dataset.

### Documentación
- `README.md`: instrucciones de instalación, ejecución y estructura.
- `docs/arquitectura.md`: este documento.
- `docs/declaracion_ia.md`: declaración de uso de IA generativa.

