# -*- coding: utf-8 -*-
"""
config.py - Constantes globales del proyecto Algoritmos-ETL.

Centraliza la configuracion para ETL, algoritmos y dashboard.
Evita duplicacion de constantes entre modulos.
"""

import os

# -----------------------------------------------------------------------------
# Directorio raiz del proyecto
# -----------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# Rutas de datos
# -----------------------------------------------------------------------------
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATASET_CSV = os.path.join(DATA_DIR, "dataset_maestro.csv")
BENCHMARK_CSV = os.path.join(PROJECT_ROOT, "benchmark_results.csv")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# -----------------------------------------------------------------------------
# Campos OHLCV estandar por activo
# -----------------------------------------------------------------------------
OHLCV_FIELDS = ["Open", "High", "Low", "Close", "Volume"]

# -----------------------------------------------------------------------------
# Activos del portafolio (minimo 20)
# -----------------------------------------------------------------------------
ASSET_SYMBOLS = [
    # ETFs grandes y estables (US)
    "VOO", "SPY", "IVV", "QQQ", "VTI",
    "DIA", "IWM", "EFA", "EEM", "IWD",
    # Internacionales
    "VEA", "VWO", "VGK", "EWZ", "EWG",
    # Colombia y LATAM (ADRs que funcionan en Yahoo)
    "EC",       # Ecopetrol ADR
    "AVAL",     # Grupo Aval ADR
    "CIB",      # Bancolombia ADR
    "PBR",      # Petrobras
    "BBD",      # Banco Bradesco
]

# -----------------------------------------------------------------------------
# Parametros ETL
# -----------------------------------------------------------------------------
START_YEARS_BACK = 7           # Anos de historia a descargar
MIN_SUCCESS_ASSETS = 20        # Minimo de activos descargados exitosamente
FETCH_DELAY_SECONDS = 0.3      # Pausa entre peticiones HTTP
FETCH_TIMEOUT_SECONDS = 90     # Timeout por peticion
FETCH_MAX_RETRIES = 3          # Reintentos por activo

# -----------------------------------------------------------------------------
# Parametros de analisis
# -----------------------------------------------------------------------------
SMA_WINDOWS = [20, 50]         # Periodos para medias moviles simples
TRADING_DAYS_PER_YEAR = 252    # Dias habiles para anualizar volatilidad

# Clasificacion de riesgo por percentiles de volatilidad
RISK_PERCENTILE_LOW = 33       # <= p33 = conservador
RISK_PERCENTILE_HIGH = 66      # > p66 = agresivo

# Sliding window
DEFAULT_WINDOW_SIZE = 20       # Tamano de ventana por defecto para patrones
