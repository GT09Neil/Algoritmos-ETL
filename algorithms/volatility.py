# -*- coding: utf-8 -*-
"""
volatility.py - Calculo de volatilidad historica y clasificacion de riesgo.

Requerimiento 3 (parte 2): calcular metricas de dispersion (desviacion estandar,
volatilidad historica) para clasificar cada activo del portafolio en categorias
de riesgo: conservador, moderado, agresivo.

RESTRICCION: NO se usa numpy, pandas, scipy ni funciones de alto nivel.
Solo math y estructuras basicas de Python.

El resultado es un listado de activos ordenados por nivel de riesgo,
usando los algoritmos de ordenamiento implementados en sorting.py.
"""

import math
import os
import sys

# Asegurar imports del proyecto
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ============================================================================
# Retornos logaritmicos
# ============================================================================

def compute_log_returns(prices):
    """
    Calcula retornos logaritmicos diarios.

    Formulacion matematica:
      r_i = ln(P_i / P_{i-1})   para i = 1..n-1

    Solo incluye posiciones donde ambos precios son validos y positivos.

    Complejidad temporal: O(n).
    Complejidad espacial: O(n).
    """
    returns = []
    for i in range(1, len(prices)):
        p_prev = prices[i - 1]
        p_curr = prices[i]
        if p_prev is not None and p_curr is not None:
            try:
                fp = float(p_prev)
                fc = float(p_curr)
                if fp > 0 and fc > 0:
                    returns.append(math.log(fc / fp))
                    continue
            except (ValueError, TypeError):
                pass
        # Si no se pudo calcular, omitir (no agregar 0)
    return returns


# ============================================================================
# Volatilidad historica
# ============================================================================

def compute_historical_volatility(prices, annualize=True, trading_days=252):
    """
    Calcula la volatilidad historica de un activo a partir de sus precios.

    Formulacion matematica:
      1. Calcular retornos logaritmicos: r_i = ln(P_i / P_{i-1})
      2. Calcular media de retornos: r_bar = (1/n) * sum(r_i)
      3. Calcular desviacion estandar muestral:
         sigma = sqrt( (1/(n-1)) * sum((r_i - r_bar)^2) )
      4. Anualizar (opcional):
         sigma_anual = sigma_diaria * sqrt(trading_days)
         donde trading_days = 252 (dias habiles por ano)

    Justificacion de la anualizacion:
      Los retornos diarios tienen magnitudes muy pequenas (~0.001).
      Anualizar con sqrt(252) permite comparar con benchmarks estandar
      de la industria financiera (volatilidad anualizada tipica: 10-50%).

    Algoritmo (dos pasadas):
      Pasada 1: calcular media de retornos.
      Pasada 2: acumular suma de cuadrados de desviaciones.

    Parametros:
      prices: list[float] — precios de cierre cronologicos.
      annualize: bool — si True, multiplica por sqrt(trading_days).
      trading_days: int — dias habiles por ano (default 252).

    Retorno:
      float — volatilidad (desviacion estandar de retornos, opcionalmente anualizada).
      Retorna 0.0 si hay menos de 3 precios validos.

    Complejidad temporal: O(n) — dos pasadas lineales.
    Complejidad espacial: O(n) para la lista de retornos.
    """
    returns = compute_log_returns(prices)
    n = len(returns)
    if n < 2:
        return 0.0

    # Pasada 1: media
    total = 0.0
    for r in returns:
        total += r
    mean_r = total / n

    # Pasada 2: varianza
    sum_sq = 0.0
    for r in returns:
        diff = r - mean_r
        sum_sq += diff * diff
    variance = sum_sq / (n - 1)
    std_dev = math.sqrt(variance)

    if annualize:
        return std_dev * math.sqrt(trading_days)
    return std_dev


# ============================================================================
# Clasificacion de riesgo
# ============================================================================

def classify_risk(volatilities_dict, low_pct=33, high_pct=66):
    """
    Clasifica cada activo en una categoria de riesgo basada en su volatilidad.

    Algoritmo:
      1. Extraer todas las volatilidades en una lista.
      2. Ordenar la lista (insertion sort manual, sin sorted()).
      3. Calcular percentiles p33 y p66.
      4. Clasificar cada activo:
         - Conservador: volatilidad <= p33
         - Moderado: p33 < volatilidad <= p66
         - Agresivo: volatilidad > p66

    Calculo de percentiles (metodo de interpolacion lineal):
      Para percentil p en una lista ordenada de n valores:
        k = (p / 100) * (n - 1)
        floor_k = int(k)
        frac = k - floor_k
        percentil = valores[floor_k] + frac * (valores[floor_k+1] - valores[floor_k])

    Parametros:
      volatilities_dict: dict {symbol: float} — volatilidad por activo.
      low_pct: int — percentil para limite conservador/moderado (default 33).
      high_pct: int — percentil para limite moderado/agresivo (default 66).

    Retorno:
      list[dict] — lista de activos con keys:
        "symbol": str
        "volatility": float
        "risk_class": str ("Conservador", "Moderado", "Agresivo")
        "rank": int (1 = menor volatilidad)

    Complejidad temporal: O(k^2) para insertion sort de k activos (k~20, trivial)
                          + O(k) para clasificar.
    Complejidad espacial: O(k).
    """
    if not volatilities_dict:
        return []

    # Extraer y crear lista de (symbol, volatility)
    items = []
    for symbol in volatilities_dict:
        items.append({
            "symbol": symbol,
            "volatility": volatilities_dict[symbol],
        })

    # Insertion sort manual por volatilidad ascendente — NO usar sorted()
    for i in range(1, len(items)):
        current = items[i]
        j = i - 1
        while j >= 0 and items[j]["volatility"] > current["volatility"]:
            items[j + 1] = items[j]
            j -= 1
        items[j + 1] = current

    # Calcular percentiles
    n = len(items)
    vols_sorted = []
    for item in items:
        vols_sorted.append(item["volatility"])

    def percentile(values, p):
        """Calcula el percentil p de una lista ya ordenada."""
        k = (p / 100.0) * (len(values) - 1)
        floor_k = int(k)
        frac = k - floor_k
        if floor_k + 1 < len(values):
            return values[floor_k] + frac * (values[floor_k + 1] - values[floor_k])
        return values[floor_k]

    p_low = percentile(vols_sorted, low_pct)
    p_high = percentile(vols_sorted, high_pct)

    # Clasificar
    result = []
    for rank, item in enumerate(items, start=1):
        vol = item["volatility"]
        if vol <= p_low:
            risk_class = "Conservador"
        elif vol <= p_high:
            risk_class = "Moderado"
        else:
            risk_class = "Agresivo"

        result.append({
            "symbol": item["symbol"],
            "volatility": vol,
            "risk_class": risk_class,
            "rank": rank,
        })

    return result


def analyze_portfolio_risk(asset_prices_dict, annualize=True, trading_days=252):
    """
    Analiza el riesgo de todo el portafolio: calcula volatilidad por activo
    y genera la clasificacion completa.

    Parametros:
      asset_prices_dict: dict {symbol: list[float]} — precios por activo.
      annualize: bool
      trading_days: int

    Retorno:
      dict con keys:
        "volatilities": dict {symbol: float}
        "classifications": list[dict] (ordenado por volatilidad)
        "thresholds": dict {"p33": float, "p66": float}
        "summary": dict {"conservador": int, "moderado": int, "agresivo": int}

    Complejidad temporal: O(k * n) donde k = activos, n = dias por activo.
    Complejidad espacial: O(k * n) para retornos + O(k) para resultados.
    """
    volatilities = {}
    for symbol in asset_prices_dict:
        prices = asset_prices_dict[symbol]
        vol = compute_historical_volatility(
            prices, annualize=annualize, trading_days=trading_days)
        volatilities[symbol] = vol

    classifications = classify_risk(volatilities)

    # Calcular thresholds
    n = len(classifications)
    vols_sorted = []
    for c in classifications:
        vols_sorted.append(c["volatility"])

    p33 = 0.0
    p66 = 0.0
    if n > 0:
        k33 = (33.0 / 100.0) * (n - 1)
        floor33 = int(k33)
        frac33 = k33 - floor33
        p33 = vols_sorted[floor33]
        if floor33 + 1 < n:
            p33 += frac33 * (vols_sorted[floor33 + 1] - vols_sorted[floor33])

        k66 = (66.0 / 100.0) * (n - 1)
        floor66 = int(k66)
        frac66 = k66 - floor66
        p66 = vols_sorted[floor66]
        if floor66 + 1 < n:
            p66 += frac66 * (vols_sorted[floor66 + 1] - vols_sorted[floor66])

    # Conteo por categoria
    summary = {"Conservador": 0, "Moderado": 0, "Agresivo": 0}
    for c in classifications:
        rc = c["risk_class"]
        if rc in summary:
            summary[rc] += 1

    return {
        "volatilities": volatilities,
        "classifications": classifications,
        "thresholds": {"p33": p33, "p66": p66},
        "summary": summary,
    }


# ============================================================================
# Pruebas rapidas
# ============================================================================

if __name__ == "__main__":
    print("=== Pruebas de volatility.py ===\n")

    # Datos sinteticos
    import random
    random.seed(42)

    # Simular 3 activos con distinta volatilidad
    def simulate_prices(start, daily_vol, n=100):
        prices = [start]
        for _ in range(n - 1):
            ret = random.gauss(0, daily_vol)
            prices.append(prices[-1] * math.exp(ret))
        return prices

    assets = {
        "LOW_VOL": simulate_prices(100, 0.005, 200),   # baja volatilidad
        "MED_VOL": simulate_prices(50, 0.015, 200),    # media
        "HIGH_VOL": simulate_prices(30, 0.035, 200),   # alta
    }

    # Calcular volatilidades
    for sym, prices in assets.items():
        vol = compute_historical_volatility(prices)
        print("  {}: vol anualizada = {:.4f} ({:.2f}%)".format(sym, vol, vol * 100))

    # Clasificacion
    result = analyze_portfolio_risk(assets)
    print("\nClasificacion de riesgo:")
    for c in result["classifications"]:
        print("  #{} {}: vol={:.4f} -> {}".format(
            c["rank"], c["symbol"], c["volatility"], c["risk_class"]))

    print("\nUmbrales: p33={:.4f}, p66={:.4f}".format(
        result["thresholds"]["p33"], result["thresholds"]["p66"]))
    print("Resumen:", result["summary"])

    # Verificaciones
    assert result["classifications"][0]["volatility"] <= result["classifications"][-1]["volatility"]
    assert result["classifications"][0]["risk_class"] == "Conservador"
    assert result["classifications"][-1]["risk_class"] == "Agresivo"

    print("\n=== Todas las pruebas OK ===")
