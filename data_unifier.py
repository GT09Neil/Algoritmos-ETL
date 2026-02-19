# -*- coding: utf-8 -*-
"""
data_unifier.py - Unificación de múltiples activos en un único dataset maestro.

Maneja diferencias de calendario bursátil: cada activo tiene sus propias fechas
(por mercado, festivos, etc.). Se construye un calendario maestro con todas las
fechas únicas, se alinean los activos a ese calendario (insertando filas con None
donde no hay dato) y se genera un dataset consolidado.

Estructuras: list, dict, set. No se usa pandas.
"""


def build_master_calendar(all_assets_data):
    """
    Construye el conjunto ordenado de todas las fechas presentes en cualquier activo.

    Algoritmo formal:
      Entrada: all_assets_data = dict { symbol_1: [row_1, ...], symbol_2: [...], ... }
               Cada row es un dict con clave "Date" (str YYYY-MM-DD).
      Salida: lista de fechas (strings) ordenada cronológicamente, sin duplicados.

      Pseudocódigo:
        all_dates <- set()
        para cada symbol en all_assets_data:
          para cada row en all_assets_data[symbol]:
            all_dates.add(row["Date"])
        master_calendar <- sorted(all_dates)
        retornar master_calendar

    Complejidad temporal: O(N log N).
      - Recorrer todos los activos y todas las filas: O(N) donde N = total de
        fechas contadas (con repetición entre activos).
      - Convertir a set no aumenta el orden (las inserciones son O(1) amortizado).
      - sorted() sobre el set de fechas únicas: si hay U fechas únicas, O(U log U).
      - En notación del enunciado, N se refiere al total de fechas únicas; entonces
        el costo dominante es sorted: O(N log N).

    Justificación de estructuras:
      - set: para reunir fechas únicas en O(1) por inserción y evitar duplicados.
      - list ordenada: para tener un orden cronológico definido (YYYY-MM-DD ordena
        lexicográficamente igual que cronológico).
    """
    all_dates = set()
    for symbol in all_assets_data:
        rows = all_assets_data[symbol]
        for row in rows:
            d = row.get("Date")
            if d is not None:
                all_dates.add(d)
    return sorted(all_dates)


def align_assets_to_calendar(all_assets_data, master_calendar):
    """
    Alinea cada activo al calendario maestro: para cada fecha del calendario,
    incluye una fila con los datos del activo si existen, o una fila con None
    en los campos numéricos si ese día no hay dato para ese activo.

    Algoritmo formal:
      Entrada: all_assets_data = dict symbol -> list of dict (datos por activo).
               master_calendar = list de fechas ordenadas.
      Salida: dict symbol -> list of dict; cada lista tiene exactamente
              len(master_calendar) elementos, en el mismo orden que master_calendar.
              Cada dict tiene "Date" y los campos del activo (Open, High, Low, Close, Volume);
              si no había dato para esa fecha, los campos numéricos son None.

      Pseudocódigo:
        aligned <- {}
        para cada symbol en all_assets_data:
          list_to_dict <- dict()   # fecha -> row
          para cada row en all_assets_data[symbol]:
            list_to_dict[row["Date"]] <- row
          aligned_list <- []
          para cada date en master_calendar:
            si date en list_to_dict:
              aligned_list.append(list_to_dict[date])
            si no:
              aligned_list.append({"Date": date, "Open": None, "High": None, "Low": None, "Close": None, "Volume": None})
          aligned[symbol] <- aligned_list
        retornar aligned

    Complejidad temporal: O(k · n).
      - k = número de activos, n = número de fechas en master_calendar.
      - Por cada activo: convertir lista a dict O(n_asset) donde n_asset = filas del activo;
        luego recorrer master_calendar O(n) y para cada fecha hacer búsqueda en dict O(1).
      - En total por activo: O(n_asset + n); sumando sobre activos: O(N_data + k·n).
        El enunciado expresa el costo como O(k·n) asumiendo n como tamaño del calendario
        y que el costo dominante es la construcción de la lista alineada de tamaño n
        para cada uno de los k activos.

    Justificación del uso de dict (fecha -> fila):
      - Acceso por fecha en O(1) al rellenar la lista alineada. Si se mantuviera
        solo la lista, para cada fecha del calendario habría que buscar en la lista
        del activo (O(n_asset) por fecha), dando O(n · n_asset) por activo. Con dict
        el costo por activo es O(n_asset) + O(n) = O(n + n_asset).
    """
    aligned = {}
    for symbol in all_assets_data:
        rows = all_assets_data[symbol]
        date_to_row = {}
        for row in rows:
            d = row.get("Date")
            if d is not None:
                date_to_row[d] = dict(row)
        aligned_list = []
        for date in master_calendar:
            if date in date_to_row:
                aligned_list.append(date_to_row[date])
            else:
                aligned_list.append({
                    "Date": date,
                    "Open": None,
                    "High": None,
                    "Low": None,
                    "Close": None,
                    "Volume": None,
                })
        aligned[symbol] = aligned_list
    return aligned


def build_master_dataset(aligned_data):
    """
    Construye el dataset maestro unificado: una lista de diccionarios, cada uno
    con "Date" y una columna por activo para Close (ej. VOO_Close, EC_Close).

    Algoritmo formal:
      Entrada: aligned_data = dict symbol -> list of dict; todas las listas tienen
               la misma longitud y el mismo orden de fechas (Date en cada fila).
      Salida: list of dict con keys "Date" y "SYMBOL_Close" para cada symbol.
              Cada elemento corresponde a una fecha; los valores Close pueden ser None.

      Pseudocódigo:
        symbols <- lista de claves de aligned_data (orden estable)
        n <- longitud de cualquier lista en aligned_data (ej. aligned_data[symbols[0]])
        master <- []
        para i en 0..n-1:
          row <- {"Date": aligned_data[symbols[0]][i]["Date"]}
          para cada symbol en symbols:
            row[symbol + "_Close"] <- aligned_data[symbol][i].get("Close")
          master.append(row)
        retornar master

    Complejidad temporal: O(k · n).
      - k = número de activos, n = número de filas (fechas).
      - Un bucle sobre n; dentro, un bucle sobre k para leer Close de cada activo.
      - Acceso a aligned_data[symbol][i] es O(1) (list por índice, dict por clave).

    Justificación estructura de salida:
      - list de dict permite exportar a CSV de forma natural (una fila por elemento,
        columnas = claves del dict). El uso de dict por fila permite O(1) por
        acceso a columna al generar o escribir.
    """
    symbols = sorted(aligned_data.keys())
    if not symbols:
        return []
    n = len(aligned_data[symbols[0]])
    master = []
    for i in range(n):
        row = {"Date": aligned_data[symbols[0]][i]["Date"]}
        for symbol in symbols:
            row[symbol + "_Close"] = aligned_data[symbol][i].get("Close")
        master.append(row)
    return master
