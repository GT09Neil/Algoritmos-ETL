# -*- coding: utf-8 -*-
"""
data_fetcher.py - Módulo de descarga de datos financieros históricos.

Requerimiento: Descarga mediante peticiones HTTP explícitas a APIs públicas.
NO se usa yfinance ni pandas_datareader. Solo: requests, urllib, json, csv.

API utilizada: Yahoo Finance Chart API (endpoint público que devuelve JSON).
Documentación informal: el endpoint es conocido y usado por múltiples clientes.
Construimos la URL manualmente y parseamos la respuesta con json.

Estructuras de datos:
- list: para secuencia ordenada de registros (orden temporal preservado).
- dict: para cada registro (acceso O(1) por clave: 'Date', 'Open', etc.).
Complejidad de acceso por fecha en lista: O(n) búsqueda lineal; para unificación
posterior se puede convertir a dict keyed by date si se necesita O(1).
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# -----------------------------------------------------------------------------
# Constantes: construcción manual de la URL del API
# -----------------------------------------------------------------------------
# Base del endpoint (sin query string). Yahoo Finance Chart v8.
_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
# Intervalo de velas: 1d = diario
_INTERVAL = "1d"
# User-Agent para evitar bloqueos por parte del servidor (petición tipo navegador)
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _date_to_unix(date_str):
    """
    Convierte fecha en formato YYYY-MM-DD a timestamp Unix (segundos).
    Usado para period1 y period2 en la URL.
    Complejidad: O(1).
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


def _unix_to_date(timestamp):
    """
    Convierte timestamp Unix a string YYYY-MM-DD.
    Complejidad: O(1).
    """
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _build_chart_url(symbol, period1, period2):
    """
    Construye la URL del gráfico sin usar librerías de finanzas.
    Parámetros:
      symbol: str (ej. "VOO", "EC")
      period1, period2: int (Unix timestamps)
    Retorno: str URL completa.
    Complejidad: O(1).
    """
    params = {
        "period1": period1,
        "period2": period2,
        "interval": _INTERVAL,
        "events": "div,splits",  # opcional; no usamos pero suele incluirse
    }
    query = urllib.parse.urlencode(params)
    # La URL es base/symbol?query
    path = "{}/{}?{}".format(_BASE_URL, urllib.parse.quote(symbol), query)
    return path


def _do_http_get(url, timeout_seconds=90):
    """
    Realiza una petición HTTP GET explícita usando urllib (sin requests
    para minimizar dependencias; si se prefiere requests, se puede sustituir).
    Manejo de errores: excepciones por red, código HTTP != 200.
    Retorno: bytes del body. Lanza excepción en error.
    Complejidad: O(1) en términos de tamaño de datos; la red domina.
    timeout_seconds=90 para dar margen a respuestas lentas (p. ej. activos internacionales).
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            if resp.status != 200:
                raise RuntimeError("HTTP status {} for URL {}".format(resp.status, url))
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP error {}: {} for URL {}".format(e.code, e.reason, url))
    except urllib.error.URLError as e:
        raise RuntimeError("URL error: {} for URL {}".format(e.reason, url))
    except OSError as e:
        raise RuntimeError("Network/OS error: {} for URL {}".format(e, url))


def _do_http_get_with_retry(url, timeout_seconds=90, max_attempts=3, retry_delay=2):
    """
    Ejecuta _do_http_get hasta max_attempts veces. Si la excepción es por timeout
    (mensaje contiene "timed out" o "timeout"), reintenta tras retry_delay segundos.
    Otras excepciones se relanzan sin reintento.
    """
    last_err = None
    for attempt in range(max_attempts):
        try:
            return _do_http_get(url, timeout_seconds=timeout_seconds)
        except RuntimeError as e:
            last_err = e
            err_msg = str(e).lower()
            if ("timed out" in err_msg or "timeout" in err_msg) and attempt < max_attempts - 1:
                time.sleep(retry_delay)
                continue
            raise
    raise last_err


def _parse_chart_json(raw_bytes):
    """
    Parsea el JSON de la respuesta del Chart API.
    No se usa ningún parser de alto nivel para finanzas; solo json.loads
    y recorrido explícito de la estructura.
    Estructura esperada (simplificada):
      chart -> result -> [0] -> timestamp (list), indicators -> quote -> [0] -> open, high, low, close, volume (lists)
    Retorno: list of dict con keys: Date, Open, High, Low, Close, Volume.
    Valores None donde el API no devuelve dato.
    Complejidad temporal: O(n) con n = número de puntos (días).
    Complejidad espacial: O(n) para las listas resultantes.
    """
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError("JSON decode error: {}".format(e))

    # Navegación explícita por la estructura (sin funciones mágicas)
    chart = data.get("chart")
    if chart is None:
        raise ValueError("Missing 'chart' in response")
    result_list = chart.get("result")
    if not result_list:
        raise ValueError("Empty or missing 'result' in chart")
    result = result_list[0]
    timestamps = result.get("timestamp")
    if timestamps is None:
        raise ValueError("Missing 'timestamp' in result")

    quote = result.get("indicators")
    if quote is None:
        raise ValueError("Missing 'indicators' in result")
    quote_list = quote.get("quote")
    if not quote_list:
        raise ValueError("Missing 'quote' in indicators")
    quote0 = quote_list[0]
    opens = quote0.get("open")
    highs = quote0.get("high")
    lows = quote0.get("low")
    closes = quote0.get("close")
    volumes = quote0.get("volume")
    # Asegurar listas (a veces el API devuelve null para un campo)
    if opens is None:
        opens = []
    if highs is None:
        highs = []
    if lows is None:
        lows = []
    if closes is None:
        closes = []
    if volumes is None:
        volumes = []

    n = len(timestamps)
    # Alinear longitudes: si alguna lista es más corta, rellenar con None
    def pad_to(lst, length, fill=None):
        out = []
        for i in range(length):
            out.append(lst[i] if i < len(lst) else fill)
        return out

    opens = pad_to(opens, n)
    highs = pad_to(highs, n)
    lows = pad_to(lows, n)
    closes = pad_to(closes, n)
    volumes = pad_to(volumes, n)

    # Construir lista de diccionarios (estructura básica solicitada)
    rows = []
    for i in range(n):
        rows.append({
            "Date": _unix_to_date(timestamps[i]),
            "Open": opens[i] if opens[i] is not None else None,
            "High": highs[i] if highs[i] is not None else None,
            "Low": lows[i] if lows[i] is not None else None,
            "Close": closes[i] if closes[i] is not None else None,
            "Volume": int(volumes[i]) if volumes[i] is not None else None,
        })
    return rows


def fetch_asset_data(symbol, start_date, end_date, delay_seconds=0.2):
    """
    Descarga datos históricos diarios para un activo.

    Algoritmo:
      1. Convertir start_date y end_date a Unix (O(1)).
      2. Construir URL (O(1)).
      3. GET HTTP (tiempo de red).
      4. Parsear JSON y extraer listas (O(n)).
      5. Construir lista de dicts (O(n)).
    Complejidad temporal total: O(n) donde n = número de días devueltos.
    Complejidad espacial: O(n).

    Parámetros:
      symbol: str (símbolo del activo, ej. "VOO", "EC")
      start_date: str "YYYY-MM-DD"
      end_date: str "YYYY-MM-DD"
      delay_seconds: float; pausa entre peticiones para no saturar el servidor.

    Retorno: list of dict. Cada dict tiene keys: Date, Open, High, Low, Close, Volume.
    En error HTTP o de parsing, lanza excepción.
    """
    period1 = _date_to_unix(start_date)
    period2 = _date_to_unix(end_date)
    url = _build_chart_url(symbol, period1, period2)
    raw = _do_http_get_with_retry(url, timeout_seconds=90, max_attempts=3, retry_delay=2)
    time.sleep(delay_seconds)
    return _parse_chart_json(raw)


def fetch_multiple_assets(symbols, start_date, end_date, delay_seconds=0.3, min_success=20):
    """
    Descarga datos para varios activos. Retorna un diccionario
    symbol -> list of dict (misma estructura que fetch_asset_data).
    Si un activo falla (timeout, 404, etc.) se guarda lista vacía y se continúa.
    Se lanza excepción solo si menos de min_success activos se descargan bien.

    Algoritmo: para cada símbolo, llamar fetch_asset_data y guardar en dict.
    Complejidad: O(k * n) donde k = número de símbolos y n = promedio de
    registros por símbolo. Estructura de retorno: dict con listas; acceso por
    símbolo O(1).
    """
    result = {}
    errors = []
    for sym in symbols:
        try:
            result[sym] = fetch_asset_data(sym, start_date, end_date, delay_seconds)
        except Exception as e:
            result[sym] = []
            errors.append((sym, str(e)))
            continue
    successful = sum(1 for v in result.values() if v)
    if successful < min_success:
        raise RuntimeError(
            "Solo {} activos descargados (minimo {}). Errores: {}".format(
                successful, min_success, errors
            )
        )
    return result


# -----------------------------------------------------------------------------
# Punto de entrada para pruebas
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    # Prueba 1: parsing sin red (JSON de ejemplo) - siempre funciona
    print("--- Prueba de parsing (sin red) ---")
    sample_json = b'{"chart":{"result":[{"timestamp":[1704067200,1704153600],"indicators":{"quote":[{"open":[380.0,381.5],"high":[382.0,383.0],"low":[379.0,380.5],"close":[381.0,382.5],"volume":[1000000,1200000]}]}}]}}'
    rows = _parse_chart_json(sample_json)
    print("Registros parseados:", len(rows))
    print("Primer registro:", rows[0])
    assert rows[0]["Date"] == "2024-01-01" and rows[0]["Close"] == 381.0
    print("Parsing OK.")

    if len(sys.argv) > 1 and sys.argv[1] == "--skip-network":
        print("--- Omitting network test (--skip-network) ---")
    else:
        # Prueba 2: descarga real (requiere acceso a Yahoo)
        print("--- Prueba de descarga (1 mes, VOO) ---")
        end = datetime.now()
        start = end - timedelta(days=31)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        symbols = ["VOO"]
        print("Fetching", symbols, "from", start_str, "to", end_str)
        try:
            data = fetch_multiple_assets(symbols, start_str, end_str, delay_seconds=0.1)
            for sym, r in data.items():
                print("{}: {} records".format(sym, len(r)))
                if r:
                    print("  First:", r[0])
                    print("  Last:", r[-1])
            print("Descarga OK.")
        except Exception as e:
            print("Descarga fallida (red/firewall?):", e)
            print("Ejecuta con --skip-network para solo probar parsing.")
    print("--- Fin pruebas ---")
