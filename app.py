# -*- coding: utf-8 -*-
"""
app.py - Servidor web Flask para el dashboard bursatil.

Requerimiento 4 y 5: aplicacion web funcional con visualizaciones
y analisis interactivos.

Rutas:
  Paginas HTML:
    /                   -> Dashboard principal
    /similarity         -> Comparacion de similitud entre 2 activos
    /patterns           -> Patrones detectados por activo
    /risk               -> Clasificacion de riesgo del portafolio

  API JSON:
    /api/symbols        -> Lista de activos disponibles
    /api/similarity     -> Calculo de similitud (params: a, b)
    /api/heatmap        -> Matriz de correlacion completa
    /api/candlestick/<s>-> Datos OHLCV + SMA para un activo
    /api/patterns/<s>   -> Patrones detectados en un activo
    /api/risk           -> Ranking de riesgo de todos los activos

  Exportacion:
    /export/pdf         -> Generar y descargar reporte PDF
"""

import csv
import json
import os
import sys
import time

# Asegurar imports del proyecto
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, render_template, request, jsonify

from algorithms.similarity import (compare_two_assets, pearson_correlation,
                                     euclidean_distance, dtw_distance,
                                     cosine_similarity, dtw_distance_with_path)
from algorithms.technical import compute_returns, compute_sma
from algorithms.patterns import scan_patterns
from algorithms.volatility import analyze_portfolio_risk

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
DATA_CSV = os.path.join(_ROOT, "data", "dataset_maestro.csv")
OHLCV_FIELDS = ["Open", "High", "Low", "Close", "Volume"]

app = Flask(__name__, static_folder="static", template_folder="templates")


# ---------------------------------------------------------------------------
# Carga de datos (una sola vez al iniciar)
# ---------------------------------------------------------------------------
_CACHE = {}


def _load_dataset():
    """Carga el dataset maestro en memoria. Se ejecuta una vez."""

    # Valida si esta en el cache (Ya se cargo antes?)
    # Por si acaso el cache es un diccionario global en memoria, no lo hace una y otra vez
    if "rows" in _CACHE:
        # Si esta en el cache, lo retorna
        return _CACHE["rows"], _CACHE["symbols"]

    # Si no esta en el cache, lo carga
    rows = []
    # Lee el archivo CSV y guarda las filas en la variable rows
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # Detectar simbolos
    symbols = []
    for col in rows[0].keys():
        # Busca todos los campos que terminen con _Close
        if col.endswith("_Close"):
            # Agrega el simbolo sin el _Close
            symbols.append(col.replace("_Close", ""))
    # Ordenamiento insertion sort manual
    # Esto es para que los simbolos esten ordenados alfabeticamente
    for i in range(1, len(symbols)):
        cur = symbols[i]
        j = i - 1
        while j >= 0 and symbols[j] > cur:
            symbols[j + 1] = symbols[j]
            j -= 1
        symbols[j + 1] = cur

    # Guarda en cache
    _CACHE["rows"] = rows
    # Guarda en cache
    _CACHE["symbols"] = symbols
    return rows, symbols


def _get_series(rows, symbol, field):
    """Extrae una serie de valores de un campo para un simbolo."""
    col = symbol + "_" + field
    out = []
    for r in rows:
        v = r.get(col)
        if v and v != "None" and v != "":
            try:
                out.append(float(v))
            except (ValueError, TypeError):
                out.append(None)
        else:
            out.append(None)
    return out


def _get_dates(rows):
    """Extrae la columna de fechas."""
    return [r.get("Date", "") for r in rows]


# ---------------------------------------------------------------------------
# Paginas HTML
# ---------------------------------------------------------------------------

@app.route("/")
def page_dashboard():
    _, symbols = _load_dataset()
    return render_template("dashboard.html", symbols=symbols)


@app.route("/similarity")
def page_similarity():
    _, symbols = _load_dataset()
    return render_template("similarity.html", symbols=symbols)


@app.route("/patterns")
def page_patterns():
    _, symbols = _load_dataset()
    return render_template("patterns.html", symbols=symbols)


@app.route("/risk")
def page_risk():
    _, symbols = _load_dataset()
    return render_template("risk.html", symbols=symbols)


# ---------------------------------------------------------------------------
# API: Simbolos
# ---------------------------------------------------------------------------

@app.route("/api/symbols")
def api_symbols():
    _, symbols = _load_dataset()
    return jsonify({"symbols": symbols})


# ---------------------------------------------------------------------------
# API: Similitud
# ---------------------------------------------------------------------------

@app.route("/api/similarity")
def api_similarity():
    # Carga el dataset
    rows, symbols = _load_dataset()
    # Obtiene los simbolos de los parametros GET 
    # En pocas palabras: Obtiene los simbolos, ej: sym_a = AAPL
    sym_a = request.args.get("a", "")
    sym_b = request.args.get("b", "")
    # Valida que los simbolos existan
    if sym_a not in symbols or sym_b not in symbols:
        return jsonify({"error": "Simbolo no encontrado"}), 400
    # Extrae la serie de precios para cada simbolo
    prices_a = _get_series(rows, sym_a, "Close")
    prices_b = _get_series(rows, sym_b, "Close")
    # Extrae las fechas
    dates = _get_dates(rows)
    # Registra el tiempo inicial
    t0 = time.perf_counter()
    # Compara los dos simbolos
    result = compare_two_assets(prices_a, prices_b)
    # Calcula el tiempo de ejecucion
    elapsed = time.perf_counter() - t0

    # --- Alinear precios validos para datos extra ---
    aligned_a, aligned_b, aligned_dates = [], [], []
    # Encuentra la longitud minima entre las tres series (deben ser de igual tamaño)
    n = min(len(prices_a), len(prices_b), len(dates))
    # Itera sobre las series
    for i in range(n):
        pa, pb = prices_a[i], prices_b[i]
        if pa is not None and pb is not None:
            try:
                # Convierte los precios a float
                fa, fb = float(pa), float(pb)
                # Valida que sean positivos
                if fa > 0 and fb > 0:
                    # Agrega los precios a las series alineadas
                    aligned_a.append(fa)
                    aligned_b.append(fb)
                    aligned_dates.append(dates[i])
            except (ValueError, TypeError):
                continue

    # Retornos logaritmicos
    returns_a = compute_returns(aligned_a) if len(aligned_a) > 1 else []
    returns_b = compute_returns(aligned_b) if len(aligned_b) > 1 else []

    # --- Muestreo para graficas ---

    # Esto limital el numero maximo de puntos para mejorar rendimiento
    max_pts = 200
    # Obtiene una lista de los elementos de la lista original
    # saltando de 'step' en 'step' elementos
    # Ej: sample_list([1,2,3,4,5,6], 2) -> [1,3,5]
    def sample_list(lst, step):
        return [lst[i] for i in range(0, len(lst), step)]
    # Calcula el paso para el muestreo
    step_p = max(1, len(aligned_a) // max_pts)
    step_r = max(1, len(returns_a) // max_pts)

    # Genera las graficas
    chart_dates = sample_list(aligned_dates, step_p)
    chart_a = sample_list(aligned_a, step_p)
    chart_b = sample_list(aligned_b, step_p)

    # Fechas para retornos (empiezan 1 despues de aligned_dates)
    # Usamos 1:] para saltar el primer elemento de la lista
    returns_dates = aligned_dates[1:] if len(aligned_dates) > 1 else []

    # --- Datos extra: Euclidiana (diferencias punto a punto) ---
    s_returns_a = sample_list(returns_a, step_r)
    s_returns_b = sample_list(returns_b, step_r)
    s_returns_dates = sample_list(returns_dates, step_r)
    point_diffs = []
    for i in range(len(s_returns_a)):
        # Calcula la diferencia entre los retornos de los dos simbolos
        # Se necesita para obtener una grafica de diferencias punto a punto
        point_diffs.append(round(s_returns_a[i] - s_returns_b[i], 8))

    # --- Datos extra: DTW warping path (muestreado) ---

    # Esto limita el numero maximo de puntos para mejorar el rendimiento
    dtw_step = max(1, len(returns_a) // 80)
    # Obtiene una lista de los elementos de la lista original
    # saltando de 'step' en 'step' elementos
    dtw_dates = sample_list(returns_dates, dtw_step)
    dtw_path = []
    # Calcula la ruta de warping para DTW
    # Validamos que tengamos suficientes puntos para comparar
    if len(returns_a) > 2:
        try:
            # Ejecutamos la funcion de DTW
            _, raw_path = dtw_distance_with_path(
                # Muestreamos las series de retornos
                sample_list(returns_a, dtw_step),
                sample_list(returns_b, max(1, len(returns_b) // 80))
            )
            # Calcula el paso para el muestreo
            path_step = max(1, len(raw_path) // 60)
            dtw_path = [list(p) for p in raw_path[::path_step]]
        except Exception:
            dtw_path = []

    # --- Datos extra: Coseno (normas) ---
    import math
    # Para el producto punto
    dot_val = 0.0
    # Para la norma cuadrada
    norm_a_sq = 0.0
    norm_b_sq = 0.0
    for i in range(len(returns_a)):
        # Producto punto de los retornos de los dos simbolos
        dot_val += returns_a[i] * returns_b[i]
        # Norma cuadrada de los retornos de los dos simbolos
        norm_a_sq += returns_a[i] * returns_a[i]
        norm_b_sq += returns_b[i] * returns_b[i]
    norm_a_val = math.sqrt(norm_a_sq) if norm_a_sq > 0 else 0
    norm_b_val = math.sqrt(norm_b_sq) if norm_b_sq > 0 else 0

    # Retorna un JSON con los datos para el frontend.
    return jsonify({
        "symbol_a": sym_a,
        "symbol_b": sym_b,
        "metrics": {
            "euclidean": round(result["euclidean"], 6),
            "pearson": round(result["pearson"], 6),
            "dtw": round(result["dtw"], 6),
            "cosine": round(result["cosine"], 6),
            "n_points": result["n_points"],
        },
        "time_seconds": round(elapsed, 4),
        "chart": {
            "dates": chart_dates,
            "series_a": chart_a,
            "series_b": chart_b,
        },
        "extra": {
            "returns_a": [round(v, 8) for v in s_returns_a],
            "returns_b": [round(v, 8) for v in s_returns_b],
            "returns_dates": s_returns_dates,
            "point_diffs": point_diffs,
            "dtw_path": dtw_path,
            "dtw_series_a": sample_list(returns_a, dtw_step),
            "dtw_series_b": sample_list(returns_b, max(1, len(returns_b) // 80)),
            "dtw_dates": dtw_dates,
            "cosine_norm_a": round(norm_a_val, 8),
            "cosine_norm_b": round(norm_b_val, 8),
            "cosine_dot": round(dot_val, 8),
        }
    })


# ---------------------------------------------------------------------------
# API: Heatmap de correlacion
# ---------------------------------------------------------------------------

@app.route("/api/heatmap")
def api_heatmap():
    if "heatmap" in _CACHE:
        return jsonify(_CACHE["heatmap"])

    rows, symbols = _load_dataset()
    n = len(symbols)

    # Precalcular retornos por activo
    returns_map = {}
    for sym in symbols:
        prices = _get_series(rows, sym, "Close")
        valid = [p for p in prices if p is not None]
        returns_map[sym] = compute_returns(valid)

    # Calcular matriz de correlacion
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            elif j < i:
                row.append(matrix[j][i])  # simetria
            else:
                r = pearson_correlation(returns_map[symbols[i]], returns_map[symbols[j]])
                row.append(round(r, 4))
        matrix.append(row)

    result = {"symbols": symbols, "matrix": matrix}
    _CACHE["heatmap"] = result
    return jsonify(result)


# ---------------------------------------------------------------------------
# API: Candlestick
# ---------------------------------------------------------------------------

@app.route("/api/candlestick/<symbol>")
def api_candlestick(symbol):
    rows, symbols = _load_dataset()
    if symbol not in symbols:
        return jsonify({"error": "Simbolo no encontrado"}), 400

    days = request.args.get("days", "250")
    try:
        days = int(days)
    except ValueError:
        days = 250

    dates = _get_dates(rows)
    opens = _get_series(rows, symbol, "Open")
    highs = _get_series(rows, symbol, "High")
    lows = _get_series(rows, symbol, "Low")
    closes = _get_series(rows, symbol, "Close")
    volumes = _get_series(rows, symbol, "Volume")

    # Ultimos N dias
    start = max(0, len(dates) - days)
    sl = slice(start, len(dates))

    # SMA sobre toda la serie, luego recortar
    valid_closes = [c if c is not None else 0 for c in closes]
    sma20_full = compute_sma(valid_closes, 20)
    sma50_full = compute_sma(valid_closes, 50)

    # Alinear SMA con las fechas: SMA20 empieza en indice 19, SMA50 en 49
    sma20_aligned = [None] * 19 + sma20_full
    sma50_aligned = [None] * 49 + sma50_full

    return jsonify({
        "symbol": symbol,
        "dates": dates[sl],
        "open": opens[sl],
        "high": highs[sl],
        "low": lows[sl],
        "close": closes[sl],
        "volume": volumes[sl],
        "sma20": sma20_aligned[sl],
        "sma50": sma50_aligned[sl],
    })


# ---------------------------------------------------------------------------
# API: Patrones
# ---------------------------------------------------------------------------

@app.route("/api/patterns/<symbol>")
def api_patterns(symbol):
    rows, symbols = _load_dataset()
    if symbol not in symbols:
        return jsonify({"error": "Simbolo no encontrado"}), 400

    window = request.args.get("window", "20")
    try:
        window = int(window)
    except ValueError:
        window = 20

    closes = _get_series(rows, symbol, "Close")
    opens = _get_series(rows, symbol, "Open")
    highs = _get_series(rows, symbol, "High")

    # Filtrar None para el calculo
    valid_c = [c if c is not None else 0 for c in closes]
    valid_o = [o if o is not None else 0 for o in opens]
    valid_h = [h if h is not None else 0 for h in highs]

    result = scan_patterns(valid_c, valid_o, valid_h, window_size=window)
    return jsonify({
        "symbol": symbol,
        "window_size": window,
        "consecutive_ups": result["consecutive_ups"],
        "gap_ups": {
            "total_gaps": result["gap_ups"]["total_gaps"],
            "max_gaps_in_window": result["gap_ups"]["max_gaps_in_window"],
            "window_size": result["gap_ups"]["window_size"],
        },
    })


# ---------------------------------------------------------------------------
# API: Riesgo
# ---------------------------------------------------------------------------

@app.route("/api/risk")
def api_risk():
    if "risk" in _CACHE:
        return jsonify(_CACHE["risk"])

    rows, symbols = _load_dataset()
    asset_prices = {}
    for sym in symbols:
        prices = _get_series(rows, sym, "Close")
        valid = [p for p in prices if p is not None]
        if len(valid) > 10:
            asset_prices[sym] = valid

    result = analyze_portfolio_risk(asset_prices)

    # Serializar
    classifications = []
    for c in result["classifications"]:
        classifications.append({
            "symbol": c["symbol"],
            "volatility": round(c["volatility"], 6),
            "volatility_pct": round(c["volatility"] * 100, 2),
            "risk_class": c["risk_class"],
            "rank": c["rank"],
        })

    resp = {
        "classifications": classifications,
        "thresholds": {
            "p33": round(result["thresholds"]["p33"], 6),
            "p66": round(result["thresholds"]["p66"], 6),
        },
        "summary": result["summary"],
    }
    _CACHE["risk"] = resp
    return jsonify(resp)


# ---------------------------------------------------------------------------
# Exportacion PDF
# ---------------------------------------------------------------------------

@app.route("/export/pdf")
def export_pdf():
    from visualization.pdf_export import generate_pdf
    from flask import send_file
    pdf_path = generate_pdf()
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name="reporte_bursatil.pdf",
        mimetype="application/pdf",
    )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Dashboard Bursatil ===")
    print("Cargando dataset...")
    _load_dataset()
    print("Dataset cargado. Iniciando servidor...")

    # Si existe PORT en entorno (Render/Railway), usar waitress (produccion)
    port = int(os.environ.get("PORT", 5000))
    if os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT"):
        from waitress import serve
        print("Modo PRODUCCION (waitress) en puerto {}".format(port))
        serve(app, host="0.0.0.0", port=port)
    else:
        print("Modo DESARROLLO en http://localhost:{}".format(port))
        app.run(debug=True, host="0.0.0.0", port=port)


