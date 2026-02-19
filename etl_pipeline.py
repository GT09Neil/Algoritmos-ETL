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
from datetime import datetime, timedelta, timezone

from data_fetcher import fetch_multiple_assets
from data_cleaner import (
    detect_missing_values,
    detect_inconsistencies,
    clean_with_forward_fill,
    remove_invalid_rows,
)
from data_unifier import (
    build_master_calendar,
    align_assets_to_calendar,
    build_master_dataset,
)

# -----------------------------------------------------------------------------
# Configuración: mínimo 20 activos (ETFs globales + acciones colombianas en Yahoo)
# -----------------------------------------------------------------------------
# ETFs globales (US) + colombianos que acepta el Chart API: EC, ISA.
# GEB/PFDAVAL/EXITO/NUTRESA/CELSIA dan 404 o respuesta sin timestamp en Yahoo;
# se sustituyen por ETFs US para que el pipeline corra con 22 activos.
ASSET_SYMBOLS = [
    "VOO",   # Vanguard S&P 500
    "SPY",   # SPDR S&P 500
    "EEM",   # iShares MSCI Emerging Markets
    "IVV",   # iShares Core S&P 500
    "QQQ",   # Invesco QQQ
    "VEA",   # Vanguard FTSE Developed
    "VWO",   # Vanguard FTSE Emerging
    "IEMG",  # iShares Core MSCI Emerging
    "VTI",   # Vanguard Total Stock Market
    "SCHF",  # Schwab International Equity
    "VGK",   # Vanguard FTSE Europe
    "EWZ",   # iShares MSCI Brazil
    "EWG",   # iShares MSCI Germany
    "FXI",   # iShares China Large-Cap
    "EC",    # Ecopetrol (Colombia)
    "ISA",   # ISA (Colombia)
    "DIA",   # SPDR Dow Jones Industrial Average
    "EFA",   # iShares MSCI EAFE
    "IWD",   # iShares Russell 1000 Value
    "VB",    # Vanguard Small-Cap
    "VTV",   # Vanguard Value
    "IWM",   # iShares Russell 2000
]

# Nombre del archivo de salida
OUTPUT_CSV = "dataset_maestro.csv"


def run_etl():
    """
    Ejecuta el pipeline ETL completo.

    Algoritmo:
      1. Calcular fecha actual y fecha hace 5 años (O(1)).
      2. Descargar datos por activo (fetch por símbolo; fallos se reportan).
      3. Por cada activo: detectar faltantes, detectar inconsistencias,
         forward fill en Close, eliminar filas inválidas.
      4. Construir calendario maestro con todas las fechas únicas.
      5. Alinear cada activo al calendario maestro.
      6. Construir dataset maestro (Date + SYMBOL_Close).
      7. Exportar a CSV e imprimir reporte.
    """
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_dt = now - timedelta(days=5 * 365)
    start_date = start_dt.strftime("%Y-%m-%d")

    print("=== Pipeline ETL ===\n")
    print("Rango de fechas: {} a {} (5 años)".format(start_date, end_date))
    print("Activos solicitados: {}".format(len(ASSET_SYMBOLS)))

    # --- Extracción: fetch_multiple_assets (tolera fallos por activo; exige mínimo 20) ---
    try:
        all_assets_data = fetch_multiple_assets(
            ASSET_SYMBOLS, start_date, end_date, delay_seconds=0.3, min_success=20
        )
    except Exception as e:
        print("Error en descarga:", e)
        print("Revisar símbolos (ej. tickers colombianos en Yahoo) y conexión.")
        return

    # Usar solo activos con datos (algunos pueden haber fallado por timeout/404)
    all_assets_data = {k: v for k, v in all_assets_data.items() if v}
    failed = [s for s in ASSET_SYMBOLS if s not in all_assets_data]
    if failed:
        print("Activos no descargados (timeout/404): {}".format(failed))
    print("Activos descargados: {}".format(len(all_assets_data)))

    # --- Reportes de limpieza por activo ---
    missing_per_asset = {}
    inconsistencies_per_asset = {}
    corrections_applied = {}
    cleaned_data = {}

    for symbol in all_assets_data:
        asset_data = all_assets_data[symbol]
        missing_count, missing_positions = detect_missing_values(asset_data)
        missing_per_asset[symbol] = (missing_count, missing_positions)
        inconsistencies = detect_inconsistencies(asset_data)
        inconsistencies_per_asset[symbol] = inconsistencies

        # Aplicar forward fill solo a Close (impacto algorítmico documentado en data_cleaner)
        clean_with_forward_fill(asset_data)
        # Eliminar filas sin Close válido
        cleaned = remove_invalid_rows(asset_data)
        cleaned_data[symbol] = cleaned
        corrections_applied[symbol] = len(asset_data) - len(cleaned)

    # --- Unificación ---
    master_calendar = build_master_calendar(cleaned_data)
    aligned_data = align_assets_to_calendar(cleaned_data, master_calendar)
    master_dataset = build_master_dataset(aligned_data)

    # --- Exportar CSV ---
    if not master_dataset:
        print("Dataset maestro vacío; no se escribe CSV.")
    else:
        fieldnames = ["Date"] + [s + "_Close" for s in sorted(cleaned_data.keys())]
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in master_dataset:
                writer.writerow(row)
        print("\nArchivo exportado: {}".format(OUTPUT_CSV))

    # --- Reporte impreso ---
    print("\n--- Reporte ---")
    print("Registros por activo (después de limpieza):")
    for symbol in sorted(cleaned_data.keys()):
        print("  {}: {}".format(symbol, len(cleaned_data[symbol])))
    print("\nValores faltantes detectados (antes de limpieza):")
    for symbol in sorted(missing_per_asset.keys()):
        count, positions = missing_per_asset[symbol]
        print("  {}: {} celdas faltantes en OHLCV (filas con al menos un faltante: {})".format(
            symbol, count, len(positions)))
    print("\nInconsistencias encontradas (High<Low, Close/Open fuera de rango):")
    for symbol in sorted(inconsistencies_per_asset.keys()):
        anom = inconsistencies_per_asset[symbol]
        print("  {}: {} anomalías".format(symbol, len(anom)))
    print("\nCorrecciones aplicadas (filas eliminadas por Close faltante):")
    for symbol in sorted(corrections_applied.keys()):
        print("  {}: {} filas eliminadas".format(symbol, corrections_applied[symbol]))
    print("\nCalendario maestro: {} fechas únicas.".format(len(master_calendar)))
    print("Dataset maestro: {} filas, {} columnas (Date + _Close por activo).".format(
        len(master_dataset), len(master_dataset[0]) if master_dataset else 0))
    print("\n=== Fin pipeline ETL ===")


if __name__ == "__main__":
    run_etl()
