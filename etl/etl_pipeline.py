# -*- coding: utf-8 -*-
"""
etl_pipeline.py - Pipeline ETL completo: Extracción, Transformación y Carga.

Orquesta data_fetcher (extracción), data_cleaner (transformación/limpieza) y
data_unifier (unificación y calendario maestro), y exporta el dataset maestro a CSV.

Requerimiento: mínimo 5 años de datos, mínimo 20 activos (acciones colombianas
y/o ETFs globales). Sin yfinance, sin pandas_datareader, sin pandas; solo
estructuras básicas y csv para exportar.
"""

import csv
import os
from datetime import datetime, timedelta, timezone

from .data_fetcher import fetch_multiple_assets
from .data_cleaner import (
    detect_missing_values,
    detect_inconsistencies,
    clean_with_forward_fill,
    remove_invalid_rows,
)
from .data_unifier import (
    build_master_calendar,
    align_assets_to_calendar,
    build_master_dataset,
)


def _isort(lst):
    """Insertion sort manual sobre lista de strings. Sin sorted()."""
    for i in range(1, len(lst)):
        current = lst[i]
        j = i - 1
        while j >= 0 and lst[j] > current:
            lst[j + 1] = lst[j]
            j -= 1
        lst[j + 1] = current
    return lst

# -----------------------------------------------------------------------------
# Configuración: mínimo 20 activos (ETFs globales + acciones colombianas en Yahoo)
# -----------------------------------------------------------------------------
# ETFs globales (US) + colombianos que acepta el Chart API: EC, ISA.
# GEB/PFDAVAL/EXITO/NUTRESA/CELSIA dan 404 o respuesta sin timestamp en Yahoo;
# se sustituyen por ETFs US para que el pipeline corra con 22 activos.
ASSET_SYMBOLS = [
    # ETFs grandes y estables
    "VOO",
    "SPY",
    "IVV",
    "QQQ",
    "VTI",
    "DIA",
    "IWM",
    "EFA",
    "EEM",
    "IWD",

    # Internacionales
    "VEA",
    "VWO",
    "VGK",
    "EWZ",
    "EWG",

    # Colombia y LATAM que sí funcionan
    "EC",      # Ecopetrol ADR
    "AVAL",    # Grupo Aval ADR
    "CIB",     # Bancolombia ADR
    "PBR",     # Petrobras
    "BBD",     # Banco Bradesco
]

# Nombre del archivo de salida (relativo a la raíz del proyecto)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
OUTPUT_CSV = os.path.join(_DATA_DIR, "dataset_maestro.csv")


def run_etl():
    """
    Ejecuta el pipeline ETL completo.

    Algoritmo:
      1. Calcular fecha actual y fecha hace 7 años (O(1)).
      2. Descargar datos por activo (fetch por símbolo; fallos se reportan).
      3. Por cada activo: detectar faltantes, detectar inconsistencias,
         forward fill en Close, eliminar filas inválidas.
      4. Construir calendario maestro con todas las fechas únicas.
      5. Alinear cada activo al calendario maestro.
      6. Construir dataset maestro (Date + SYMBOL_Close).
      7. Exportar a CSV e imprimir reporte.
    """

    # =========================================================
    # 1. DEFINIR FECHAS DEL PIPELINE
    # =========================================================

    # Obtiene la fecha
    now = datetime.now(timezone.utc)
    # Convertir fecha final a string formato YYYY-MM-DD
    end_date = now.strftime("%Y-%m-%d")
    # Calcula la fecha de 7 años
    start_dt = now - timedelta(days=7 * 365)
    # lo convierte a string
    start_date = start_dt.strftime("%Y-%m-%d")

    print("=== Pipeline ETL ===\n")
    print("Rango de fechas: {} a {} (7 años)".format(start_date, end_date))
    print("Activos solicitados: {}".format(len(ASSET_SYMBOLS)))

    # =========================================================
    # 2. EXTRACCIÓN DE DATOS FINANCIEROS
    # =========================================================

    # --- Extracción: fetch_multiple_assets (tolera fallos por activo; exige mínimo 20) ---
    try:

        # Descargar múltiples activos financieros
        #
        # Parámetros:
        #   ASSET_SYMBOLS -> lista de tickers
        #   start_date -> fecha inicial
        #   end_date -> fecha final
        #   delay_seconds -> pausa entre requests
        #   min_success -> mínimo de activos válidos
        #
        # Resultado:
        #   {
        #      "AAPL": [...],
        #      "TSLA": [...],
        #      ...
        #   }
        all_assets_data = fetch_multiple_assets(
            ASSET_SYMBOLS, start_date, end_date, delay_seconds=0.3, min_success=20
        )
    except Exception as e:
        print("Error en descarga:", e)
        print("Revisar símbolos (ej. tickers colombianos en Yahoo) y conexión.")
        return

    # =========================================================
    # 3. ELIMINAR ACTIVOS VACÍOS
    # =========================================================

    # Mantener únicamente activos con datos
    #
    # Comprensión de diccionario:
    #   k -> símbolo
    #   v -> lista de datos
    #
    # if v:
    #   conserva solo listas no vacías

    all_assets_data = {k: v for k, v in all_assets_data.items() if v}
    failed = [s for s in ASSET_SYMBOLS if s not in all_assets_data]
    if failed:
        print("Activos no descargados (timeout/404): {}".format(failed))
    print("Activos descargados: {}".format(len(all_assets_data)))

    # --- Reportes de limpieza por activo ---

    # Guardará:
    #   símbolo -> (cantidad missing, posiciones)
    missing_per_asset = {}

    # Guardará:
    #   símbolo -> lista de inconsistencias
    inconsistencies_per_asset = {}

    # Guardará:
    #   símbolo -> número de correcciones aplicadas
    corrections_applied = {}

    # Guardará:
    #   símbolo -> datos limpios finales
    cleaned_data = {}

    # =========================================================
    # 4. LIMPIEZA INDIVIDUAL POR ACTIVO
    # =========================================================

    # Recorrer cada activo descargado
    for symbol in all_assets_data:

        # Obtener serie temporal del activo
        asset_data = all_assets_data[symbol]

        # -----------------------------------------------------
        # DETECTAR VALORES FALTANTES
        # -----------------------------------------------------

        # Retorna:
        #   missing_count -> total de None
        #   missing_positions -> filas afectadas
        missing_count, missing_positions = detect_missing_values(asset_data)

        # Guardar reporte
        missing_per_asset[symbol] = (
            missing_count,
            missing_positions
        )

        # -----------------------------------------------------
        # DETECTAR INCONSISTENCIAS LÓGICAS
        # -----------------------------------------------------

        # Detectar anomalías financieras:
        #   High < Low
        #   Close fuera de rango
        #   Open fuera de rango
        inconsistencies = detect_inconsistencies(asset_data)

        # Guardar anomalías detectadas
        inconsistencies_per_asset[symbol] = inconsistencies

        # -----------------------------------------------------
        # FORWARD FILL
        # -----------------------------------------------------

        # Aplicar imputación forward fill sobre Close
        #
        # Si falta un Close:
        #   usa el último valor válido conocido
        #
        # Ejemplo:
        #   [10, None, None, 15]
        #
        # Se convierte en:
        #   [10, 10, 10, 15]
        clean_with_forward_fill(asset_data)

        # -----------------------------------------------------
        # ELIMINAR FILAS INVÁLIDAS
        # -----------------------------------------------------

        # Eliminar filas donde Close sigue siendo None
        cleaned = remove_invalid_rows(asset_data)

        # Guardar dataset limpio del activo
        cleaned_data[symbol] = cleaned

        # Calcular cuántas filas fueron eliminadas
        corrections_applied[symbol] = len(asset_data) - len(cleaned)

    # =========================================================
    # 5. CONTRUIR CALENDARIO MAESTRO
    # =========================================================

    # --- Unificación ---

    # Conjunto global de fechas unicas
    master_calendar = build_master_calendar(cleaned_data)
    # Alineamos todos los activos en el mismo eje temporal, esto es crítico para trabajar
    # Con Pearson, DTW, Eu...Etc (Req 2)
    aligned_data = align_assets_to_calendar(cleaned_data, master_calendar)
    
    # Ahora por ultimo creamos el dataset maestro
    master_dataset = build_master_dataset(aligned_data)

    # --- Exportar CSV ---
    if not master_dataset:
        print("Dataset maestro vacío; no se escribe CSV.")
    else:
        # Asegurar que el directorio de salida exista
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

        sym_keys = list(cleaned_data.keys())
        _isort(sym_keys)
        _OHLCV = ("Open", "High", "Low", "Close", "Volume")
        fieldnames = ["Date"]
        for s in sym_keys:
            for field in _OHLCV:
                fieldnames.append(s + "_" + field)
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in master_dataset:
                writer.writerow(row)
        print("\nArchivo exportado: {}".format(OUTPUT_CSV))

    # --- Reporte impreso ---
    print("\n--- Reporte ---")
    print("Registros por activo (después de limpieza):")
    _sorted_ck = list(cleaned_data.keys())
    _isort(_sorted_ck)
    for symbol in _sorted_ck:
        print("  {}: {}".format(symbol, len(cleaned_data[symbol])))
    print("\nValores faltantes detectados (antes de limpieza):")
    _sorted_mk = list(missing_per_asset.keys())
    _isort(_sorted_mk)
    for symbol in _sorted_mk:
        count, positions = missing_per_asset[symbol]
        print("  {}: {} celdas faltantes en OHLCV (filas con al menos un faltante: {})".format(
            symbol, count, len(positions)))
    print("\nInconsistencias encontradas (High<Low, Close/Open fuera de rango):")
    _sorted_ik = list(inconsistencies_per_asset.keys())
    _isort(_sorted_ik)
    for symbol in _sorted_ik:
        anom = inconsistencies_per_asset[symbol]
        print("  {}: {} anomalías".format(symbol, len(anom)))
    print("\nCorrecciones aplicadas (filas eliminadas por Close faltante):")
    _sorted_cak = list(corrections_applied.keys())
    _isort(_sorted_cak)
    for symbol in _sorted_cak:
        print("  {}: {} filas eliminadas".format(symbol, corrections_applied[symbol]))
    print("\nCalendario maestro: {} fechas únicas.".format(len(master_calendar)))
    print("Dataset maestro: {} filas, {} columnas (Date + OHLCV por activo).".format(
        len(master_dataset), len(master_dataset[0]) if master_dataset else 0))
    print("\n=== Fin pipeline ETL ===")


if __name__ == "__main__":
    run_etl()
