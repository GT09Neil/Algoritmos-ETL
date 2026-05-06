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

from algorithms.similarity import compare_two_assets, pearson_correlation
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
    if "rows" in _CACHE:
        return _CACHE["rows"], _CACHE["symbols"]

    rows = []
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # Detectar simbolos
    symbols = []
    for col in rows[0].keys():
        if col.endswith("_Close"):
            symbols.append(col.replace("_Close", ""))
    # Insertion sort manual
    for i in range(1, len(symbols)):
        cur = symbols[i]
        j = i - 1
        while j >= 0 and symbols[j] > cur:
            symbols[j + 1] = symbols[j]
            j -= 1
        symbols[j + 1] = cur

    _CACHE["rows"] = rows
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
    rows, symbols = _load_dataset()
    sym_a = request.args.get("a", "")
    sym_b = request.args.get("b", "")
    if sym_a not in symbols or sym_b not in symbols:
        return jsonify({"error": "Simbolo no encontrado"}), 400

    prices_a = _get_series(rows, sym_a, "Close")
    prices_b = _get_series(rows, sym_b, "Close")
    dates = _get_dates(rows)

    t0 = time.perf_counter()
    result = compare_two_assets(prices_a, prices_b)
    elapsed = time.perf_counter() - t0

    # Series para graficar (muestrear si es muy largo)
    max_points = 500
    step = 1
    if len(dates) > max_points:
        step = len(dates) // max_points

    chart_dates = []
    chart_a = []
    chart_b = []
    for i in range(0, len(dates), step):
        chart_dates.append(dates[i])
        chart_a.append(prices_a[i])
        chart_b.append(prices_b[i])

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


