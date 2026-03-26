# -*- coding: utf-8 -*-
"""
main.py - Orquestador principal del proyecto Algoritmos-ETL.

Integra el pipeline ETL (extraccion, limpieza, unificacion de datos
financieros) con el modulo de algoritmos de ordenamiento y la medicion
de tiempos de ejecucion.

Flujo:
  1. Ejecutar ETL (o cargar CSV existente con --skip-etl)
  2. Ordenamiento de registros completos (Date + Close) con 12 algoritmos
  3. Extraccion de los 15 dias con mayor volumen y ordenamiento
  4. Benchmark agregado + diagrama de barras ASCII
  5. Exportar resultados a CSV

Uso:
  python main.py                    # ETL completo + analisis
  python main.py --skip-etl         # Solo analisis (requiere CSV existente)
  python main.py --symbols VOO SPY  # Analisis solo para ciertos activos

Restricciones:
  - NO se usa yfinance, pandas_datareader, pandas.
  - NO se usan funciones built-in de ordenamiento (sort, sorted, heapq).
  - TODO es reproducible automaticamente.
"""

import csv
import os
import sys

# Agregar el directorio raiz al path para imports
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from etl.etl_pipeline import run_etl, OUTPUT_CSV, ASSET_SYMBOLS
from algorithms.sorting import ALGORITHMS, run_sort
from benchmarks.timing import (
    run_benchmarks,
    verify_results,
    print_report,
    export_results_csv,
    print_bar_chart,
)

BENCHMARK_CSV = os.path.join(_ROOT, "benchmark_results.csv")

# Los 12 algoritmos participan: la key multi-criterio se codifica
# como un entero unico (compatible con algoritmos no comparativos).
COMPARISON_ALGS = [
    "TimSort", "Comb Sort", "Selection Sort", "Tree Sort",
    "Pigeonhole Sort", "Bucket Sort",
    "QuickSort", "HeapSort", "Bitonic Sort", "Gnome Sort",
    "Binary Insertion Sort", "Radix Sort"
]


def parse_args(argv):
    """
    Parser de argumentos simple (sin argparse para mantener minimalismo).
    Retorna dict con opciones.
    """
    opts = {
        "skip_etl": False,
        "symbols": None,
    }
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--skip-etl":
            opts["skip_etl"] = True
        elif arg == "--symbols":
            symbols = []
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                symbols.append(argv[i])
                i += 1
            opts["symbols"] = symbols
            continue
        i += 1
    return opts


def load_csv_data(filepath):
    """
    Carga el dataset maestro desde CSV.
    Retorna: (fieldnames, rows) donde rows es lista de dict.
    Sin pandas; solo csv.
    Complejidad: O(n * k) donde n = filas, k = columnas.
    """
    rows = []
    fieldnames = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames if reader.fieldnames else []
        for row in reader:
            rows.append(row)
    return fieldnames, rows


# ============================================================================
# REQUERIMIENTO 1: Ordenamiento de registros completos (Date + Close)
# ============================================================================

def build_records_for_symbol(rows, symbol):
    """
    Construye lista de registros completos {Date, Close, Volume} para un activo
    a partir del dataset maestro.

    Solo incluye filas con Close valido (no None/vacio).
    Complejidad: O(n) donde n = numero de filas del CSV.
    """
    close_col = symbol + "_Close"
    volume_col = symbol + "_Volume"
    records = []
    for row in rows:
        close_val = row.get(close_col)
        if close_val is not None and close_val != "" and close_val != "None":
            try:
                close_float = float(close_val)
            except (ValueError, TypeError):
                continue
            vol_raw = row.get(volume_col)
            vol = None
            if vol_raw is not None and vol_raw != "" and vol_raw != "None":
                try:
                    vol = int(float(vol_raw))
                except (ValueError, TypeError):
                    pass
            records.append({
                "Date": row.get("Date", ""),
                "Close": close_float,
                "Volume": vol,
                "Symbol": symbol,
            })
    return records


def multi_key_date_close(record):
    """
    Funcion key para ordenamiento multi-criterio:
      1. Fecha de cotizacion (ascendente)
      2. Precio de cierre (ascendente) — desempate

    Codifica ambos criterios en un unico entero para compatibilidad
    con algoritmos no-comparativos (Pigeonhole, Bucket, Radix).

    Codificacion compacta:
      date_compact = (year - 2000) * 366 + (month - 1) * 31 + day
        -> rango ~2500 para 7 anos de datos (2019-2026)
      close_cents = int(round(close * 100))
        -> rango ~60_000 para precios tipicos de ETFs/acciones
      resultado = date_compact * 100_000 + close_cents

    El multiplicador 100_000 garantiza que close_cents (< 100_000 para
    precios < $1000) nunca interfiere con la parte de fecha.

    Rango total tipico: ~2500 * 100_000 = 250_000_000.
    Viable para Pigeonhole (250M holes ~1GB), Bucket y Radix.

    Complejidad: O(1) por llamada.
    """
    date_str = record["Date"]
    year = int(date_str[0:4])
    month = int(date_str[5:7])
    day = int(date_str[8:10])
    date_compact = (year - 2000) * 366 + (month - 1) * 31 + day
    close_cents = int(round(record["Close"] * 100))
    return date_compact * 100_000 + close_cents


def run_record_sort_benchmark(records, symbol):
    """
    Ejecuta los 12 algoritmos sobre registros completos con key multi-criterio.
    Mide tiempos y verifica que todos producen el mismo resultado.
    """
    print("\n" + "=" * 65)
    print("  ORDENAMIENTO DE REGISTROS COMPLETOS: {}".format(symbol))
    print("  Criterio: Fecha (asc) + Close (asc) como desempate")
    print("  {} registros".format(len(records)))
    print("=" * 65)

    results = run_benchmarks(records, key=multi_key_date_close, algorithms=COMPARISON_ALGS)

    # Verificar consistencia
    all_match, discrepancies = verify_results(results)
    print_report(results, discrepancies)
    print_bar_chart(results)

    # Mostrar primeros y ultimos 5 registros del resultado
    if results:
        sorted_data = results[0]["sorted_data"]
        print("\n  Primeros 5 registros ordenados:")
        for i in range(min(5, len(sorted_data))):
            r = sorted_data[i]
            print("    {} | Close: {:>10.2f} | Vol: {}".format(
                r["Date"], r["Close"],
                "{:>12,}".format(r["Volume"]) if r["Volume"] is not None else "N/A"))
        print("  Ultimos 5 registros ordenados:")
        start_idx = len(sorted_data) - 5
        if start_idx < 0:
            start_idx = 0
        for i in range(start_idx, len(sorted_data)):
            r = sorted_data[i]
            print("    {} | Close: {:>10.2f} | Vol: {}".format(
                r["Date"], r["Close"],
                "{:>12,}".format(r["Volume"]) if r["Volume"] is not None else "N/A"))

    return results


# ============================================================================
# REQUERIMIENTO 3: Top 15 dias con mayor volumen
# ============================================================================

def extract_top_n_by_volume(records, n=15):
    """
    Extrae los N registros con mayor volumen de negociacion.
    Usa Selection Sort parcial manual (NO usa sorted/heapq).

    Algoritmo:
      1. Filtrar registros con Volume valido (no None).
      2. Copiar la lista filtrada.
      3. Ejecutar N pasadas de selection sort (seleccionar el maximo, intercambiar
         con posicion actual, repetir). Esto da los N mayores en O(N*m) donde
         m = registros con volumen valido.
      4. Retornar los N seleccionados en orden descendente.

    Complejidad: O(N * m) donde m = len(records con volumen), N = 15.
                 Mucho mejor que ordenar todo si N << m.
    """
    # Filtrar registros con Volume valido
    with_vol = []
    for r in records:
        if r["Volume"] is not None and r["Volume"] > 0:
            with_vol.append(dict(r))  # copia

    if len(with_vol) == 0:
        return []

    actual_n = n
    if actual_n > len(with_vol):
        actual_n = len(with_vol)

    # Selection sort parcial: N pasadas para encontrar los N mayores
    for i in range(actual_n):
        max_idx = i
        for j in range(i + 1, len(with_vol)):
            if with_vol[j]["Volume"] > with_vol[max_idx]["Volume"]:
                max_idx = j
        with_vol[i], with_vol[max_idx] = with_vol[max_idx], with_vol[i]

    # Los primeros actual_n son los de mayor volumen (descendente)
    top_n_desc = []
    for i in range(actual_n):
        top_n_desc.append(with_vol[i])

    # Ahora ordenar esos N ascendentemente por volumen usando insertion sort manual
    for i in range(1, len(top_n_desc)):
        current = top_n_desc[i]
        j = i - 1
        while j >= 0 and top_n_desc[j]["Volume"] > current["Volume"]:
            top_n_desc[j + 1] = top_n_desc[j]
            j -= 1
        top_n_desc[j + 1] = current

    return top_n_desc


def print_top_volume(top_records, symbol):
    """
    Imprime tabla de los registros con mayor volumen.
    """
    print("\n" + "=" * 65)
    print("  TOP {} DIAS CON MAYOR VOLUMEN: {}".format(len(top_records), symbol))
    print("  (ordenados por volumen ascendente)")
    print("=" * 65)

    if not top_records:
        print("  No hay registros con volumen valido.")
        return

    print("  {:<5s} {:<12s} {:>12s} {:>15s}".format(
        "#", "Fecha", "Close", "Volumen"))
    print("  " + "-" * 48)

    for i, r in enumerate(top_records, start=1):
        print("  {:<5d} {:<12s} {:>12.2f} {:>15,}".format(
            i, r["Date"], r["Close"], r["Volume"]))

    print("=" * 65)


# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def main():
    """Punto de entrada principal."""
    opts = parse_args(sys.argv)

    print("=" * 65)
    print("  PROYECTO ALGORITMOS-ETL")
    print("  Pipeline ETL + Algoritmos de Ordenamiento + Benchmarks")
    print("=" * 65)

    # --- Paso 1: ETL ---
    if opts["skip_etl"]:
        print("\n[ETL] Omitido (--skip-etl). Cargando CSV existente...")
        if not os.path.exists(OUTPUT_CSV):
            print("ERROR: No existe '{}'. Ejecute sin --skip-etl primero.".format(
                OUTPUT_CSV))
            return
    else:
        print("\n[ETL] Ejecutando pipeline ETL completo...")
        run_etl()

    # --- Paso 2: Cargar datos ---
    print("\n[DATOS] Cargando dataset maestro desde '{}'...".format(OUTPUT_CSV))
    fieldnames, rows = load_csv_data(OUTPUT_CSV)
    print("  {} filas, {} columnas cargadas.".format(len(rows), len(fieldnames)))

    # Determinar activos disponibles
    close_cols = []
    for col in fieldnames:
        if col.endswith("_Close"):
            close_cols.append(col.replace("_Close", ""))

    if opts["symbols"]:
        target_symbols = opts["symbols"]
    else:
        target_symbols = close_cols

    print("  Activos disponibles: {}".format(len(close_cols)))
    print("  Activos seleccionados: {}".format(target_symbols))

    # --- Paso 3: Por activo — Ordenamiento de registros + Top 15 volumen ---
    print("\n[ALGORITMOS] {} algoritmos disponibles: {}".format(
        len(ALGORITHMS), list(ALGORITHMS.keys())))

    all_agg_records = []

    for symbol in target_symbols:
        records = build_records_for_symbol(rows, symbol)
        if not records:
            print("\n  {} - Sin datos, omitido.".format(symbol))
            continue

        # REQUERIMIENTO 1: Ordenamiento multi-key de registros completos
        run_record_sort_benchmark(records, symbol)

        # REQUERIMIENTO 3: Top 15 por volumen
        top_15 = extract_top_n_by_volume(records, n=15)
        print_top_volume(top_15, symbol)

        # Acumular para benchmark agregado
        for r in records:
            all_agg_records.append(r)

    # --- Paso 4: Benchmark agregado + diagrama de barras ---
    if all_agg_records:
        print("\n" + "=" * 65)
        print("  BENCHMARK AGREGADO (todos los activos combinados)")
        print("  {} registros totales".format(len(all_agg_records)))
        print("=" * 65)

        agg_results = run_benchmarks(all_agg_records, key=multi_key_date_close, algorithms=COMPARISON_ALGS)
        all_match, discrepancies = verify_results(agg_results)
        print_report(agg_results, discrepancies)

        # REQUERIMIENTO 2: Diagrama de barras
        print_bar_chart(agg_results)

        # Exportar
        export_results_csv(agg_results, BENCHMARK_CSV)
    else:
        print("\n  No hay datos para benchmark agregado.")

    print("\n" + "=" * 65)
    print("  FIN DEL PROYECTO")
    print("=" * 65)


if __name__ == "__main__":
    main()
