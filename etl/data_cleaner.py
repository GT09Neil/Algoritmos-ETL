# -*- coding: utf-8 -*-
"""
data_cleaner.py - Módulo de detección y limpieza de datos financieros.

Detecta valores faltantes e inconsistencias en listas de diccionarios
(estructura devuelta por data_fetcher). No usa pandas ni funciones mágicas;
solo estructuras básicas: list, dict, set.

Claves esperadas por fila: Date, Open, High, Low, Close, Volume.

Justificación de técnicas de limpieza (Requerimiento 1):
  - Corrección (forward fill): se aplica solo a Close cuando hay huecos aislados;
    preserva la longitud de la serie y es estándar en series temporales; el impacto
    en análisis posteriores es bajo si los faltantes son pocos.
  - Eliminación de registros: se eliminan filas donde Close es None (tras intentar
    forward fill), porque sin precio de cierre la fila no es usable para retornos
    ni para alinear con otros activos; evita propagar valores nulos al dataset
    maestro y mantiene consistencia entre activos.
  - No se usa interpolación lineal aquí para no inventar precios entre extremos
    y mantener la interpretación económica clara (precio observado o último conocido).
"""

# Campos numéricos que se inspeccionan para faltantes e inconsistencias
_NUMERIC_KEYS = ("Open", "High", "Low", "Close", "Volume")


def detect_missing_values(asset_data):
    """
    Detecta valores None en los campos Open, High, Low, Close y Volume.

    Algoritmo formal:
      Entrada: asset_data = [row_0, row_1, ..., row_{n-1}], cada row_i es un dict.
      Salida: (total_count, positions) donde total_count es el número de celdas
              con None en esos campos y positions es una lista de índices de fila
              que tienen al menos un valor faltante.

      Pseudocódigo:
        count <- 0
        positions <- []  (lista para mantener orden de detección; set no preserva orden)
        seen_positions <- set()  (evitar duplicados en positions)
        para cada índice i en 0..n-1:
          para cada key en (Open, High, Low, Close, Volume):
            si asset_data[i][key] es None:
              count <- count + 1
              si i no está en seen_positions: añadir i a positions y a seen_positions
        retornar (count, positions)

    Complejidad temporal: O(n).
      - Una sola pasada sobre la lista de n elementos.
      - Por cada fila se hace un número constante (5) de accesos a dict, O(1) cada uno.
      - Inserción en set y en lista es O(1) amortizado.
    Complejidad espacial: O(n) en el peor caso (positions podría tener hasta n índices).

    Estructura de datos: list para asset_data (acceso por índice O(1)); dict por fila
    (acceso por clave O(1)). Se usa set auxiliar para no duplicar índices en positions.
    """
    if not asset_data:
        return 0, []
    count = 0
    positions = []
    seen_positions = set()
    for i in range(len(asset_data)):
        row = asset_data[i]
        for key in _NUMERIC_KEYS:
            if row.get(key) is None:
                count += 1
                if i not in seen_positions:
                    seen_positions.add(i)
                    positions.append(i)
    return count, positions


def detect_inconsistencies(asset_data):
    """
    Detecta anomalías lógicas en OHLCV: High < Low, Close fuera de [Low, High],
    Open fuera de [Low, High].

    Algoritmo formal:
      Entrada: asset_data = lista de dict con Open, High, Low, Close, Volume.
      Salida: lista de anomalías; cada elemento es un dict con al menos:
              {"index": i, "type": str, "row": dict} para identificar fila y tipo.

      Reglas:
        - Inconsistencia 1: High < Low (inviable en un candle).
        - Inconsistencia 2: Close no está en [Low, High] (cuando Low, High, Close no son None).
        - Inconsistencia 3: Open no está en [Low, High] (cuando Low, High, Open no son None).
      Se ignoran filas donde algún valor necesario sea None (no se puede validar rango).

    Complejidad temporal: O(n).
      - Una pasada sobre n filas; por fila un número constante de comparaciones y accesos.
    Complejidad espacial: O(a) donde a = número de anomalías (lista de retorno).

    Estructura de datos: list para recorrido secuencial; dict por fila para acceso O(1)
    por campo.
    """
    anomalies = []
    for i in range(len(asset_data)):
        row = asset_data[i]
        low = row.get("Low")
        high = row.get("High")
        open_ = row.get("Open")
        close = row.get("Close")
        if low is None or high is None:
            continue
        if high < low:
            anomalies.append({
                "index": i,
                "type": "High_less_than_Low",
                "row": dict(row),
            })
        if close is not None:
            if close < low or close > high:
                anomalies.append({
                    "index": i,
                    "type": "Close_outside_Low_High_range",
                    "row": dict(row),
                })
        if open_ is not None:
            if open_ < low or open_ > high:
                anomalies.append({
                    "index": i,
                    "type": "Open_outside_Low_High_range",
                    "row": dict(row),
                })
    return anomalies


def clean_with_forward_fill(asset_data):
    """
    Rellena valores None en Close con el último valor válido anterior (forward fill).

    Algoritmo formal:
      Entrada: asset_data = lista de dict (se modifica in-place en el campo Close).
      Salida: misma lista; los Close None se sustituyen por el último Close no None
              visto al recorrer la lista de izquierda a derecha.
      Si el primer elemento tiene Close None, se deja None (no hay valor previo).

    Justificación del impacto algorítmico:
      - Forward fill es una heurística estándar en series temporales: asume que
        el precio se mantiene hasta la siguiente observación. Introduce correlación
        artificial si hay muchos faltantes consecutivos; para pocos faltantes el
        sesgo es limitado.
      - Una sola pasada O(n): se mantiene una variable "last_valid" y se actualiza
        al encontrar un Close no None; si es None, se asigna last_valid.

    Complejidad temporal: O(n). Una pasada, trabajo constante por fila.
    Complejidad espacial: O(1) adicional (solo la variable last_valid).

    Estructura de datos: se modifica el dict de cada fila in-place; no se crean
    estructuras auxiliares proporcionales a n.
    """
    if not asset_data:
        return asset_data
    last_valid = None
    for i in range(len(asset_data)):
        row = asset_data[i]
        if row.get("Close") is not None:
            last_valid = row["Close"]
        elif last_valid is not None:
            row["Close"] = last_valid
    return asset_data


def remove_invalid_rows(asset_data):
    """
    Elimina filas con datos críticos faltantes (Close es None o todos los OHLC faltantes).

    Algoritmo formal:
      Entrada: asset_data = lista de dict.
      Salida: nueva lista que contiene solo las filas donde Close no es None.
      Criterio de "crítico": sin Close no se puede usar la fila para análisis
      de precios ni para alinear con otros activos; por tanto se elimina la fila.

    Complejidad temporal: O(n).
      - Una pasada: se construye una nueva lista appendando solo las filas válidas.
      - Cada append es O(1) amortizado.
    Complejidad espacial: O(n) para la nueva lista (en el peor caso no se elimina nada).

    Estructura de datos: list para iterar; nueva list para resultado (preserva orden).
    No se usa remove in-place sobre la lista original para evitar O(n) por eliminación
    y así mantener O(n) total.
    """
    result = []
    for i in range(len(asset_data)):
        row = asset_data[i]
        if row.get("Close") is not None:
            result.append(row)
    return result
