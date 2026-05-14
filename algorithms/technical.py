# -*- coding: utf-8 -*-
"""
technical.py - Funciones de analisis tecnico implementadas manualmente.

Modulo de soporte para los algoritmos de similitud (similarity.py),
volatilidad (volatility.py) y visualizaciones (candlestick con SMA).

Todas las funciones operan sobre listas de Python (list[float]).
NO se usa numpy, pandas, scipy ni ninguna libreria de alto nivel.
Solo se usa el modulo math de la biblioteca estandar.

Funciones:
  - compute_returns: retornos logaritmicos diarios
  - compute_simple_returns: retornos porcentuales simples
  - compute_mean: media aritmetica
  - compute_std_dev: desviacion estandar muestral
  - compute_sma: media movil simple (Simple Moving Average)
"""

import math


# ============================================================================
# Media aritmetica
# ============================================================================

def compute_mean(values):
    """
    Calcula la media aritmetica de una lista de numeros.

    Formulacion matematica:
      x_bar = (1/n) * sum(x_i, i=1..n)

    Algoritmo:
      1. Recorrer la lista acumulando la suma.
      2. Dividir por n.

    Parametros:
      values: list[float] — secuencia de valores numericos.

    Retorno:
      float — media aritmetica.
      Lanza ValueError si la lista esta vacia.

    Complejidad temporal: O(n) — una pasada.
    Complejidad espacial: O(1) — solo un acumulador.

    Estructura de datos: list para acceso secuencial O(1) por indice.
    """
    n = len(values)
    if n == 0:
        raise ValueError("compute_mean: lista vacia")
    total = 0.0
    for i in range(n):
        total += values[i]
    return total / n


# ============================================================================
# Desviacion estandar muestral
# ============================================================================

def compute_std_dev(values):
    """
    Calcula la desviacion estandar muestral (con divisor n-1).

    Formulacion matematica:
      sigma = sqrt( (1/(n-1)) * sum((x_i - x_bar)^2, i=1..n) )

    Algoritmo (dos pasadas):
      Pasada 1: calcular la media x_bar.
      Pasada 2: acumular sum((x_i - x_bar)^2).
      Dividir por (n-1), tomar raiz cuadrada.

    Justificacion de dos pasadas vs una sola (formula de Welford):
      Dos pasadas es numericamente mas estable para datos financieros
      con valores grandes y varianza relativamente pequena.

    Parametros:
      values: list[float]

    Retorno:
      float — desviacion estandar muestral.
      Lanza ValueError si len(values) < 2.

    Complejidad temporal: O(n) — dos pasadas lineales.
    Complejidad espacial: O(1) — solo acumuladores.
    """
    n = len(values)
    if n < 2:
        raise ValueError("compute_std_dev: se necesitan al menos 2 valores")
    mean = compute_mean(values)
    sum_sq = 0.0
    for i in range(n):
        diff = values[i] - mean
        sum_sq += diff * diff
    return math.sqrt(sum_sq / (n - 1))


# ============================================================================
# Retornos logaritmicos
# ============================================================================

def compute_returns(prices):
    """
    Calcula retornos logaritmicos diarios a partir de una serie de precios.

    Formulacion matematica:
      r_i = ln(P_i / P_{i-1})   para i = 1..n-1

    Propiedades:
      - Los retornos logaritmicos son aditivos en el tiempo:
        r_total = sum(r_i), lo cual facilita analisis de periodos.
      - Son simetricos: una ganancia del x% y una perdida del x%
        producen retornos de magnitud similar (a diferencia de retornos simples).
      - Aproximan bien los retornos simples para variaciones pequenas.

    Algoritmo:
      1. Para cada par consecutivo (P_{i-1}, P_i), calcular ln(P_i / P_{i-1}).
      2. Omitir pares donde P_{i-1} <= 0 (logaritmo no definido).

    Parametros:
      prices: list[float] — serie de precios de cierre, ordenada cronologicamente.

    Retorno:
      list[float] — lista de n-1 retornos logaritmicos.

    Complejidad temporal: O(n) — una pasada.
    Complejidad espacial: O(n) — lista de retornos de tamano n-1.
    """

    # En pocas palabras esto lo que hace es retornar los cambios (Ej: subio 10%, etc)
    # Para que sea comparable

    # Cantidad de precios
    n = len(prices)

    # Valida el minimo (Necesitamos el actual y el anterior para medir el cambio)
    if n < 2:
        return []
    # Crea la lista resultado
    returns = []
    # Empezamos con 1 porque necesitamos medir el i-1 (Actual y anterior)
    for i in range(1, n):
        # Validamos que los precios sea positivos (Porque manejamos logaritmos)
        if prices[i - 1] > 0 and prices[i] > 0:
            # Aquí es donde buscamos la diferencia 
            # Ej: 110 / 100 = 1.1  a lo anterior le hacemos ln(1.1) = 0.0953 
            # Osea que hay un retorno positivo
            returns.append(math.log(prices[i] / prices[i - 1]))
        else:
            # Precio cero o negativo: retorno indefinido, se omite
            returns.append(0.0)
    return returns


# ============================================================================
# Retornos simples (porcentuales)
# ============================================================================

def compute_simple_returns(prices):
    """
    Calcula retornos simples (porcentuales) diarios.

    Formulacion matematica:
      r_i = (P_i - P_{i-1}) / P_{i-1}   para i = 1..n-1

    Parametros:
      prices: list[float]

    Retorno:
      list[float] — lista de n-1 retornos simples.

    Complejidad temporal: O(n).
    Complejidad espacial: O(n).
    """
    n = len(prices)
    if n < 2:
        return []
    returns = []
    for i in range(1, n):
        if prices[i - 1] != 0:
            returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
        else:
            returns.append(0.0)
    return returns


# ============================================================================
# Media movil simple (SMA)
# ============================================================================

def compute_sma(prices, window):
    """
    Calcula la media movil simple (Simple Moving Average) con ventana deslizante.

    Formulacion matematica:
      SMA(i) = (1/w) * sum(P_j, j=i-w+1..i)   para i = w-1..n-1

    Algoritmo optimizado con acumulador deslizante:
      1. Calcular la suma de los primeros 'window' elementos.
      2. SMA[0] = suma / window.
      3. Para cada posicion subsiguiente:
         - Sumar el nuevo elemento que entra a la ventana.
         - Restar el elemento que sale de la ventana.
         - SMA[k] = suma_actualizada / window.

    Esto evita recalcular la suma completa de la ventana en cada paso.

    Parametros:
      prices: list[float] — serie de precios.
      window: int — tamano de la ventana (periodo de la SMA).

    Retorno:
      list[float] — lista de longitud (n - window + 1) con valores SMA.
      Los primeros (window-1) periodos no tienen SMA (datos insuficientes).
      Retorna lista vacia si len(prices) < window.

    Complejidad temporal: O(n) — una pasada tras la suma inicial.
    Complejidad espacial: O(n) — lista de resultados.

    Nota: cada elemento de la lista de salida corresponde a la posicion
    i = window-1, window, ..., n-1 de la serie original.
    """
    n = len(prices)
    if n < window or window < 1:
        return []

    # Suma inicial de la primera ventana
    current_sum = 0.0
    for i in range(window):
        current_sum += prices[i]

    sma_values = []
    sma_values.append(current_sum / window)

    # Deslizar la ventana: agregar el nuevo, quitar el viejo
    for i in range(window, n):
        current_sum += prices[i]        # entra el nuevo
        current_sum -= prices[i - window]  # sale el viejo
        sma_values.append(current_sum / window)

    return sma_values


# ============================================================================
# Pruebas rapidas
# ============================================================================

if __name__ == "__main__":
    print("=== Pruebas de technical.py ===\n")

    # Datos de prueba
    prices = [100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 110.0, 108.0]

    # Media
    m = compute_mean(prices)
    print("Precios:", prices)
    print("Media: {:.4f}".format(m))

    # Desviacion estandar
    sd = compute_std_dev(prices)
    print("Desv. estandar: {:.4f}".format(sd))

    # Retornos logaritmicos
    rets = compute_returns(prices)
    print("Retornos log:", ["{:.6f}".format(r) for r in rets])

    # Retornos simples
    srets = compute_simple_returns(prices)
    print("Retornos simples:", ["{:.6f}".format(r) for r in srets])

    # SMA(3)
    sma3 = compute_sma(prices, 3)
    print("SMA(3):", ["{:.2f}".format(v) for v in sma3])
    assert len(sma3) == len(prices) - 3 + 1

    # SMA(5)
    sma5 = compute_sma(prices, 5)
    print("SMA(5):", ["{:.2f}".format(v) for v in sma5])

    print("\n=== Todas las pruebas OK ===")
