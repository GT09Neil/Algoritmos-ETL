# -*- coding: utf-8 -*-
"""
timing.py - Módulo de medición de tiempos de ejecución para algoritmos de
ordenamiento.

Usa time.perf_counter() para medir con resolución de nanosegundos.
Cada algoritmo se ejecuta sobre una COPIA de los datos para garantizar
comparaciones justas.

Exporta resultados a CSV y muestra tabla comparativa en consola.
No usa pandas; solo csv y estructuras básicas.
"""

import csv
import os
import time

from algorithms.sorting import ALGORITHMS


def _copy_list(data):
    """Copia superficial de una lista. O(n)."""
    result = []
    for item in data:
        result.append(item)
    return result


def measure_algorithm(algorithm_name, algorithm_func, data, key=None):
    """
    Mide el tiempo de ejecución de un algoritmo de ordenamiento.

    Algoritmo:
      1. Crear copia de los datos (O(n)).
      2. Registrar tiempo inicial con perf_counter().
      3. Ejecutar algoritmo sobre la copia.
      4. Registrar tiempo final.
      5. Calcular diferencia.

    Parámetros:
      algorithm_name: str (nombre para el reporte).
      algorithm_func: callable (la función de ordenamiento).
      data: list (datos originales, NO se modifican).
      key: callable o None (función de extracción de valor).

    Retorno: dict con keys:
      - "algorithm": nombre
      - "n": tamaño de entrada
      - "time_seconds": tiempo en segundos
      - "sorted_data": lista ordenada resultante (para verificación)

    Complejidad temporal: O(f(n)) donde f es la complejidad del algoritmo.
    Complejidad espacial: O(n) adicional por la copia + lo que use el algoritmo.
    """
    data_copy = _copy_list(data)
    n = len(data_copy)

    start = time.perf_counter()
    sorted_data = algorithm_func(data_copy, key=key)
    end = time.perf_counter()

    elapsed = end - start

    return {
        "algorithm": algorithm_name,
        "n": n,
        "time_seconds": elapsed,
        "sorted_data": sorted_data,
    }


def run_benchmarks(data, key=None, algorithms=None):
    """
    Ejecuta todos los algoritmos registrados (o un subconjunto) sobre los
    datos proporcionados y recopila tiempos de ejecución.

    Parámetros:
      data: list de valores a ordenar.
      key: callable o None.
      algorithms: list de nombres o None para ejecutar todos.

    Retorno: list of dict con los resultados de cada algoritmo.
    """
    if algorithms is None:
        alg_items = list(ALGORITHMS.items())
    else:
        alg_items = []
        for name in algorithms:
            if name in ALGORITHMS:
                alg_items.append((name, ALGORITHMS[name]))

    results = []
    total = len(alg_items)

    for idx, (name, func) in enumerate(alg_items, start=1):
        print("  [{}/{}] Ejecutando {}...".format(idx, total, name), end="")
        result = measure_algorithm(name, func, data, key=key)
        print(" {:.6f}s".format(result["time_seconds"]))
        results.append(result)

    return results


def verify_results(results):
    """
    Verifica que todos los algoritmos produjeron el mismo resultado ordenado.
    Compara los primeros 5 y últimos 5 elementos de cada resultado.

    Retorno: (all_match: bool, discrepancies: list of str)
    """
    if len(results) <= 1:
        return True, []

    reference = results[0]["sorted_data"]
    ref_name = results[0]["algorithm"]
    discrepancies = []

    for r in results[1:]:
        other = r["sorted_data"]
        if len(reference) != len(other):
            discrepancies.append("{} tiene longitud {} vs {} ({})".format(
                r["algorithm"], len(other), len(reference), ref_name))
            continue
        match = True
        for i in range(len(reference)):
            if reference[i] != other[i]:
                match = False
                break
        if not match:
            discrepancies.append(
                "{} difiere de {} en índice {}".format(
                    r["algorithm"], ref_name, i))

    return len(discrepancies) == 0, discrepancies


def print_report(results, discrepancies=None):
    """
    Imprime tabla comparativa de tiempos en consola.
    """
    print("\n" + "=" * 65)
    print("{:<25s} {:>10s} {:>15s} {:>10s}".format(
        "Algoritmo", "n", "Tiempo (s)", "Tiempo (ms)"))
    print("-" * 65)

    for r in results:
        ms = r["time_seconds"] * 1000
        print("{:<25s} {:>10d} {:>15.6f} {:>10.3f}".format(
            r["algorithm"], r["n"], r["time_seconds"], ms))

    print("=" * 65)

    if discrepancies:
        print("\n[!] DISCREPANCIAS encontradas:")
        for d in discrepancies:
            print("  - {}".format(d))
    else:
        print("\n[OK] Todos los algoritmos producen el mismo resultado ordenado.")


def export_results_csv(results, filepath):
    """
    Exporta resultados de benchmark a CSV.
    """
    fieldnames = ["algorithm", "n", "time_seconds", "time_ms"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({
                "algorithm": r["algorithm"],
                "n": r["n"],
                "time_seconds": r["time_seconds"],
                "time_ms": r["time_seconds"] * 1000,
            })
    print("\nResultados exportados a: {}".format(filepath))


def print_bar_chart(results, bar_width=50):
    """
    Genera un diagrama de barras ASCII de los tiempos de ejecucion.
    Los algoritmos se ordenan por tiempo ascendente usando insertion sort
    manual (NO sorted()).

    Parametros:
      results: list of dict con keys "algorithm", "time_seconds".
      bar_width: int, ancho maximo de la barra mas larga (caracteres).

    Complejidad: O(k^2) para insertion sort sobre k algoritmos (k=12, trivial).
                 O(k) para renderizar.
    """
    if not results:
        return

    # Copiar resultados para no mutar el original
    items = []
    for r in results:
        items.append({
            "algorithm": r["algorithm"],
            "time_ms": r["time_seconds"] * 1000,
        })

    # Insertion sort manual por time_ms (ascendente) — NO usar sorted()
    for i in range(1, len(items)):
        current = items[i]
        j = i - 1
        while j >= 0 and items[j]["time_ms"] > current["time_ms"]:
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current

    # Encontrar el tiempo maximo para escalar las barras
    max_time = items[0]["time_ms"]
    for it in items:
        if it["time_ms"] > max_time:
            max_time = it["time_ms"]
    if max_time <= 0:
        max_time = 1  # evitar division por cero

    print("\n" + "=" * 65)
    print("  DIAGRAMA DE BARRAS - Tiempos de Ejecucion (ms)")
    print("  (ordenados de menor a mayor)")
    print("=" * 65)

    for it in items:
        # Calcular longitud proporcional de la barra
        ratio = it["time_ms"] / max_time
        filled = int(ratio * bar_width)
        if filled < 1 and it["time_ms"] > 0:
            filled = 1  # minimo 1 caracter si hay tiempo > 0
        bar = "#" * filled
        label = "{:<25s}".format(it["algorithm"])
        time_str = "{:>10.3f} ms".format(it["time_ms"])
        print("  {} |{} {}".format(label, bar, time_str))

    print("=" * 65)

