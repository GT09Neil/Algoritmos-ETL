# -*- coding: utf-8 -*-
"""
similarity.py - Algoritmos de similitud entre series de tiempo financieras.

Requerimiento 2 del proyecto: implementar al menos 4 algoritmos de similitud.

RESTRICCION CRITICA: NO se usa scipy, numpy, sklearn, ni ninguna funcion de
alto nivel que encapsule medidas de similitud. Solo se usa math de la
biblioteca estandar. Todas las implementaciones son explicitas y analizables.

Algoritmos implementados:
  1. Distancia Euclidiana (euclidean_distance)
  2. Correlacion de Pearson (pearson_correlation)
  3. Dynamic Time Warping - DTW (dtw_distance)
  4. Similitud por Coseno (cosine_similarity)

Cada algoritmo incluye:
  - Formulacion matematica completa
  - Descripcion algoritmica detallada (pseudocodigo)
  - Analisis de complejidad temporal y espacial
  - Justificacion de estructuras de datos
  - Interpretacion del resultado

Las funciones operan sobre listas de Python (list[float]).
Tipicamente se les pasan series de retornos (no precios crudos) para
que las comparaciones sean significativas entre activos de distinta escala.
"""

import math


# ============================================================================
# 1. Distancia Euclidiana
# ============================================================================

def euclidean_distance(series_a, series_b):
    """
    Calcula la distancia euclidiana entre dos series de tiempo.

    Formulacion matematica:
      d(x, y) = sqrt( sum( (x_i - y_i)^2, i=1..n ) )

    Esta metrica mide la "distancia recta" en un espacio n-dimensional
    entre dos puntos representados por las series. Es sensible a la
    magnitud absoluta de los valores; por ello se recomienda aplicarla
    sobre retornos normalizados o estandarizados.

    Algoritmo:
      Entrada: series_a = [a_1, ..., a_n], series_b = [b_1, ..., b_n]
      Precondicion: len(series_a) == len(series_b) (series alineadas)

      sum_sq <- 0
      para i en 0..n-1:
        diff <- series_a[i] - series_b[i]
        sum_sq <- sum_sq + diff * diff
      retornar sqrt(sum_sq)

    Parametros:
      series_a: list[float] — primera serie (retornos o precios).
      series_b: list[float] — segunda serie (misma longitud).

    Retorno:
      float — distancia euclidiana (>= 0).
      Interpretacion: menor valor = series mas similares.
      d = 0 si y solo si las series son identicas.

    Complejidad temporal: O(n) — una sola pasada.
    Complejidad espacial: O(1) — solo un acumulador escalar.

    Estructura de datos: list[float] para ambas series; acceso por indice O(1).
    No se crean estructuras auxiliares.
    """

    # Basicamente mide la distancia

    # Validamos que las series tengan la misma longitud. Si no tienen
    # la misma longitud, no se puede calcular la distancia euclidiana.
    n = len(series_a)
    if n != len(series_b):
        raise ValueError(
            "euclidean_distance: series de distinta longitud ({} vs {})".format(
                n, len(series_b)))

    # Si la serie esta vacia, no se puede calcular la distancia euclidiana.
    if n == 0:
        return 0.0

    # Inicializamos la suma de los cuadrados de las diferencias.
    sum_sq = 0.0
    for i in range(n):
        diff = series_a[i] - series_b[i]
        sum_sq += diff * diff
    return math.sqrt(sum_sq)


# ============================================================================
# 2. Correlacion de Pearson
# ============================================================================

def pearson_correlation(series_a, series_b):
    """
    Calcula el coeficiente de correlacion de Pearson entre dos series.

    Formulacion matematica:
      r = sum((x_i - x_bar) * (y_i - y_bar), i=1..n)
          / sqrt( sum((x_i - x_bar)^2) * sum((y_i - y_bar)^2) )

    donde x_bar = (1/n) * sum(x_i) y y_bar = (1/n) * sum(y_i).

    Mide la relacion lineal entre dos variables. Es invariante a escala
    y traslacion, lo que la hace ideal para comparar activos financieros
    de distinta magnitud de precios.

    Algoritmo (dos pasadas para estabilidad numerica):
      Pasada 1: calcular medias x_bar, y_bar.
        x_bar <- (1/n) * sum(series_a[i], i=0..n-1)
        y_bar <- (1/n) * sum(series_b[i], i=0..n-1)

      Pasada 2: calcular sumas cruzadas.
        sum_xy <- 0
        sum_x2 <- 0
        sum_y2 <- 0
        para i en 0..n-1:
          dx <- series_a[i] - x_bar
          dy <- series_b[i] - y_bar
          sum_xy <- sum_xy + dx * dy
          sum_x2 <- sum_x2 + dx * dx
          sum_y2 <- sum_y2 + dy * dy

        denominador <- sqrt(sum_x2 * sum_y2)
        si denominador == 0: retornar 0.0 (varianza nula)
        retornar sum_xy / denominador

    Parametros:
      series_a: list[float]
      series_b: list[float] (misma longitud)

    Retorno:
      float en [-1, 1].
      Interpretacion:
        +1 = correlacion positiva perfecta (se mueven igual)
        -1 = correlacion negativa perfecta (se mueven opuesto)
         0 = sin correlacion lineal

    Complejidad temporal: O(n) — dos pasadas lineales.
    Complejidad espacial: O(1) — solo acumuladores escalares.

    Justificacion de dos pasadas:
      La formula de una sola pasada (sum(x_i * y_i) - n * x_bar * y_bar)
      es numericamente inestable para valores grandes con varianza pequena
      (cancelacion catastrofica). Dos pasadas evitan este problema a costa
      de un factor constante x2 en tiempo.
    """

    # Basicamente esta funcion mide que tanto se parecen dos series
    # en terminos de su comportamiento lineal. Es decir, si una serie
    # sube, la otra tambien sube?

    # Validamos que las series tengan la misma longitud
    n = len(series_a)
    if n != len(series_b):
        raise ValueError(
            "pearson_correlation: series de distinta longitud ({} vs {})".format(
                n, len(series_b)))

    # Si la serie tiene menos de 2 elementos, no se puede calcular la correlacion de Pearson.
    if n < 2:
        return 0.0

    # Pasada 1: calcular medias x_bar, y_bar.
    sum_a = 0.0
    sum_b = 0.0
    for i in range(n):
        sum_a += series_a[i]
        sum_b += series_b[i]
    mean_a = sum_a / n
    mean_b = sum_b / n

    # Pasada 2: sumas cruzadas y cuadradas
    sum_xy = 0.0
    sum_x2 = 0.0
    sum_y2 = 0.0
    for i in range(n):
        dx = series_a[i] - mean_a
        dy = series_b[i] - mean_b
        sum_xy += dx * dy
        sum_x2 += dx * dx
        sum_y2 += dy * dy

    denominator = math.sqrt(sum_x2 * sum_y2)
    if denominator == 0.0:
        return 0.0  # varianza nula en al menos una serie
    return sum_xy / denominator


# ============================================================================
# 3. Dynamic Time Warping (DTW)
# ============================================================================

def dtw_distance(series_a, series_b, window=None):
    """
    Calcula la distancia Dynamic Time Warping entre dos series de tiempo.

    Formulacion matematica:
      DTW encuentra la alineacion optima entre dos secuencias que minimiza
      la suma de distancias punto a punto, permitiendo deformaciones
      temporales (warping). Es especialmente util para series financieras
      que pueden mostrar patrones similares pero desfasados en el tiempo.

      Definicion recursiva:
        DTW[i][j] = |a[i] - b[j]| + min(DTW[i-1][j],      # insercion
                                         DTW[i][j-1],      # eliminacion
                                         DTW[i-1][j-1])    # coincidencia

      Condiciones de frontera:
        DTW[0][0] = |a[0] - b[0]|
        DTW[i][0] = |a[i] - b[0]| + DTW[i-1][0]   para i > 0
        DTW[0][j] = |a[0] - b[j]| + DTW[0][j-1]   para j > 0

    Algoritmo (programacion dinamica con banda de Sakoe-Chiba):
      1. Crear matriz (n x m) inicializada con infinito.
      2. DTW[0][0] = |a[0] - b[0]|.
      3. Para cada celda (i, j) dentro de la banda |i - j| <= w:
         cost = |a[i] - b[j]|
         DTW[i][j] = cost + min(DTW[i-1][j], DTW[i][j-1], DTW[i-1][j-1])
      4. Retornar DTW[n-1][m-1].

    Optimizacion con banda de Sakoe-Chiba:
      Sin banda: se evaluan todas las n*m celdas -> O(n*m).
      Con banda w: solo se evaluan celdas donde |i - j| <= w -> O(n*w).
      La banda limita cuanto desfase temporal se permite; para datos
      financieros diarios, w = 10-30 dias es razonable.

    Optimizacion de espacio:
      Se usan solo 2 filas de la matriz a la vez (fila anterior + fila actual),
      reduciendo el espacio de O(n*m) a O(m).

    Parametros:
      series_a: list[float] — primera serie (longitud n).
      series_b: list[float] — segunda serie (longitud m).
      window: int o None — ancho de banda de Sakoe-Chiba.
              Si None, se usa min(n, m) // 4 como valor por defecto.
              Si 0, se evalua toda la matriz (sin banda).

    Retorno:
      float — distancia DTW (>= 0).
      Interpretacion: menor valor = series mas similares
      (considerando posibles desfases temporales).
      d = 0 si y solo si las series son identicas.

    Complejidad temporal:
      Sin banda: O(n * m).
      Con banda w: O(n * w) donde w << m tipicamente.

    Complejidad espacial: O(m) — solo 2 filas de la matriz.

    Estructura de datos:
      - list[float] para las dos filas alternas de la matriz DP.
      - Se evita crear la matriz completa n*m para ahorrar memoria
        (para n=m=1800, la matriz completa seria ~25MB de floats).
    """

    # Basicamente esta funcion mide que tan parecidas son dos series
    # de tiempo, permitiendo que tengan desfases temporales.

    n = len(series_a)
    m = len(series_b)

    # Si alguna serie esta vacia, no se puede calcular la distancia DTW.
    if n == 0 or m == 0:
        return 0.0

    # Determinar ancho de banda
    if window is None:
        w = max(n, m) // 4
        if w < 10:
            w = 10
    elif window == 0:
        w = max(n, m)  # sin restriccion de banda
    else:
        w = window

    # Asegurar que la banda sea suficiente para alcanzar la esquina (n-1, m-1)
    min_w = abs(n - m)
    if w < min_w:
        w = min_w

    INF = float('inf')

    # Optimizacion de espacio: solo 2 filas
    # prev_row = fila i-1, curr_row = fila i
    prev_row = []
    for j in range(m):
        prev_row.append(INF)
    curr_row = []
    for j in range(m):
        curr_row.append(INF)

    # Inicializar fila 0
    for j in range(m):
        if abs(0 - j) > w:
            continue
        cost = abs(series_a[0] - series_b[j])
        if j == 0:
            prev_row[j] = cost
        else:
            prev_row[j] = cost + prev_row[j - 1]

    # Rellenar filas 1..n-1
    for i in range(1, n):
        # Resetear curr_row a INF
        for j in range(m):
            curr_row[j] = INF

        for j in range(m):
            if abs(i - j) > w:
                continue
            cost = abs(series_a[i] - series_b[j])

            # min de los 3 vecinos
            candidates = INF

            # DTW[i-1][j] — arriba
            val = prev_row[j]
            if val < candidates:
                candidates = val

            # DTW[i][j-1] — izquierda
            if j > 0:
                val = curr_row[j - 1]
                if val < candidates:
                    candidates = val

            # DTW[i-1][j-1] — diagonal
            if j > 0:
                val = prev_row[j - 1]
            else:
                val = INF
            if j == 0:
                # Solo diagonal es prev_row[-1] que no existe; usar INF
                pass
            else:
                if prev_row[j - 1] < candidates:
                    candidates = prev_row[j - 1]

            curr_row[j] = cost + candidates

        # Intercambiar filas (sin crear nuevas listas)
        prev_row, curr_row = curr_row, prev_row

    # El resultado esta en prev_row (porque se intercambiaron al final)
    return prev_row[m - 1]


# ============================================================================
# 4. Similitud por Coseno
# ============================================================================

def cosine_similarity(series_a, series_b):
    """
    Calcula la similitud por coseno entre dos series de tiempo.

    Formulacion matematica:
      cos(theta) = (a . b) / (||a|| * ||b||)

      donde:
        a . b = sum(a_i * b_i, i=1..n)          (producto punto)
        ||a|| = sqrt(sum(a_i^2, i=1..n))        (norma euclidiana)
        ||b|| = sqrt(sum(b_i^2, i=1..n))

    Mide el coseno del angulo entre los dos vectores en espacio n-dimensional.
    Es invariante a la magnitud (solo mide la "direccion"), lo que la hace
    ideal para comparar la forma de los movimientos independientemente de
    la amplitud.

    Algoritmo:
      Entrada: series_a = [a_1, ..., a_n], series_b = [b_1, ..., b_n]

      dot <- 0
      norm_a <- 0
      norm_b <- 0
      para i en 0..n-1:
        dot <- dot + series_a[i] * series_b[i]
        norm_a <- norm_a + series_a[i]^2
        norm_b <- norm_b + series_b[i]^2
      norm_a <- sqrt(norm_a)
      norm_b <- sqrt(norm_b)
      si norm_a == 0 o norm_b == 0: retornar 0.0
      retornar dot / (norm_a * norm_b)

    Parametros:
      series_a: list[float]
      series_b: list[float] (misma longitud)

    Retorno:
      float en [-1, 1].
      Interpretacion:
        +1 = vectores en la misma direccion (patrones identicos)
         0 = vectores ortogonales (sin relacion)
        -1 = vectores en direccion opuesta (patrones inversos)

    Complejidad temporal: O(n) — una sola pasada.
    Complejidad espacial: O(1) — solo tres acumuladores escalares.

    Estructura de datos: list[float] para ambas series; acceso O(1) por indice.
    """

    # Basicamente esta funcion mide que tan parecidas son dos series
    # de tiempo en terminos de su forma, independientemente de su magnitud.
    # Es decir, si una serie sube, la otra tambien sube?

    n = len(series_a)
    if n != len(series_b):
        raise ValueError(
            "cosine_similarity: series de distinta longitud ({} vs {})".format(
                n, len(series_b)))
    if n == 0:
        return 0.0

    dot = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0
    for i in range(n):
        dot += series_a[i] * series_b[i]
        norm_a_sq += series_a[i] * series_a[i]
        norm_b_sq += series_b[i] * series_b[i]

    norm_a = math.sqrt(norm_a_sq)
    norm_b = math.sqrt(norm_b_sq)

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ============================================================================
# Funciones auxiliares de alto nivel (combinar con datos del dataset)
# ============================================================================

def compare_two_assets(prices_a, prices_b):
    """
    Ejecuta los 4 algoritmos de similitud entre dos series de precios.

    Preprocesamiento:
      1. Alinear las series (usar solo posiciones donde ambas tienen dato).
      2. Calcular retornos logaritmicos (para normalizar escala).
      3. Ejecutar cada algoritmo sobre los retornos.

    Parametros:
      prices_a: list[float] — precios de cierre del activo A.
      prices_b: list[float] — precios de cierre del activo B.
                Ambas listas deben tener la misma longitud (ya alineadas
                por el calendario maestro).

    Retorno:
      dict con keys:
        "euclidean": float (distancia; menor = mas similar)
        "pearson": float (correlacion; +1 = mas similar)
        "dtw": float (distancia; menor = mas similar)
        "cosine": float (similitud; +1 = mas similar)
        "n_points": int (puntos usados en la comparacion)

    Complejidad temporal: O(n) para Euclidiana, Pearson, Coseno.
                          O(n * w) para DTW con banda w.
    """
    # Alinear: usar solo posiciones donde ambos precios son validos

    # Creamos listas alineadas
    aligned_a = []
    aligned_b = []

    # Obtenemos la longitud
    n = len(prices_a)

    # Validamos que tenga el mismo tamaño
    if n != len(prices_b):
        # Si no, usa el minimo
        n = min(len(prices_a), len(prices_b))

    # Recorre ambas series
    for i in range(n):

        # Obtenemos ambos precios
        pa = prices_a[i]
        pb = prices_b[i]

        # Comprobamos que haya algo que comparar
        if pa is not None and pb is not None:
            try:
                # Convertmos a float ambos
                fa = float(pa)
                fb = float(pb)
                # Validamos positivos (Porque utilizaremos logaritmos)
                if fa > 0 and fb > 0:
                    # Como son validos pues los agregamos
                    aligned_a.append(fa)
                    aligned_b.append(fb)
            except (ValueError, TypeError):
                # Si hay un error pues... al siguiente
                continue

    # Validamos que haya con que comparar (minimo 2)
    if len(aligned_a) < 2:

        # Si no hay datos suficientes
        return {
            "euclidean": 0.0,
            "pearson": 0.0,
            "dtw": 0.0,
            "cosine": 0.0,
            "n_points": 0,
        }

    # Calcular retornos logaritmicos
    # Importar funcion
    from algorithms.technical import compute_returns

    # Nos devuelven los retornos
    returns_a = compute_returns(aligned_a)
    returns_b = compute_returns(aligned_b)

    # Ejecutar los 4 algoritmos sobre retornos
    results = {
        "euclidean": euclidean_distance(returns_a, returns_b),
        "pearson": pearson_correlation(returns_a, returns_b),
        "dtw": dtw_distance(returns_a, returns_b),
        "cosine": cosine_similarity(returns_a, returns_b),
        "n_points": len(returns_a),
    }
    return results

# ============================================================================
# DTW con path (para visualizacion)
# ============================================================================

def dtw_distance_with_path(series_a, series_b):
    """
    Calcula DTW y retorna (distancia, warping_path).
    warping_path es una lista de tuplas (i, j) que describe la alineacion
    optima. Se usa la matriz completa para poder hacer backtracking.

    Complejidad temporal: O(n * m)
    Complejidad espacial: O(n * m)
    """
    # En cristiano podemos decir que mientras mas pequeña sea la distancia
    # entre las dos series, mas similares seran. 
    # El chiste esta en que la distancia no se mide de manera lineal
    # sino que se mide de manera que se pueda comparar una serie con otra
    # sin importar si tienen diferentes longitudes.
    n = len(series_a)
    m = len(series_b)
    if n == 0 or m == 0:
        return 0.0, []

    INF = float('inf')

    # Construir matriz completa
    D = []
    for i in range(n):
        row = []
        for j in range(m):
            row.append(INF)
        D.append(row)

    D[0][0] = abs(series_a[0] - series_b[0])
    for j in range(1, m):
        D[0][j] = abs(series_a[0] - series_b[j]) + D[0][j - 1]
    for i in range(1, n):
        D[i][0] = abs(series_a[i] - series_b[0]) + D[i - 1][0]

    for i in range(1, n):
        for j in range(1, m):
            cost = abs(series_a[i] - series_b[j])
            mn = D[i - 1][j]
            if D[i][j - 1] < mn:
                mn = D[i][j - 1]
            if D[i - 1][j - 1] < mn:
                mn = D[i - 1][j - 1]
            D[i][j] = cost + mn

    # Backtrack
    path = []
    i, j = n - 1, m - 1
    path.append((i, j))
    while i > 0 or j > 0:
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            candidates = [
                (D[i - 1][j - 1], i - 1, j - 1),
                (D[i - 1][j], i - 1, j),
                (D[i][j - 1], i, j - 1),
            ]
            best = candidates[0]
            for c in candidates[1:]:
                if c[0] < best[0]:
                    best = c
            i, j = best[1], best[2]
        path.append((i, j))

    # Invertir path
    path_reversed = []
    for k in range(len(path) - 1, -1, -1):
        path_reversed.append(path[k])

    return D[n - 1][m - 1], path_reversed




if __name__ == "__main__":
    print("=== Pruebas de similarity.py ===\n")

    # Series de prueba
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0]  # identica
    c = [5.0, 4.0, 3.0, 2.0, 1.0]  # invertida
    d = [1.1, 2.2, 2.8, 4.1, 5.2]  # similar a 'a' con ruido

    # 1. Euclidiana
    print("--- Distancia Euclidiana ---")
    print("  a vs a (identicas):", euclidean_distance(a, b))
    print("  a vs c (invertida):", euclidean_distance(a, c))
    print("  a vs d (ruido):", euclidean_distance(a, d))

    # 2. Pearson
    print("\n--- Correlacion de Pearson ---")
    print("  a vs a:", pearson_correlation(a, b))  # debe ser 1.0
    print("  a vs c:", pearson_correlation(a, c))  # debe ser -1.0
    print("  a vs d:", pearson_correlation(a, d))  # debe ser ~1.0

    # 3. DTW
    print("\n--- Dynamic Time Warping ---")
    print("  a vs a:", dtw_distance(a, b))
    print("  a vs c:", dtw_distance(a, c))
    print("  a vs d:", dtw_distance(a, d))

    # 4. Coseno
    print("\n--- Similitud por Coseno ---")
    print("  a vs a:", cosine_similarity(a, b))  # debe ser 1.0
    print("  a vs c:", cosine_similarity(a, c))  # < 1
    print("  a vs d:", cosine_similarity(a, d))  # ~1.0

    # Verificaciones
    assert euclidean_distance(a, b) == 0.0, "Distancia de identicas debe ser 0"
    assert abs(pearson_correlation(a, b) - 1.0) < 1e-10, "Pearson identicas = 1"
    assert abs(pearson_correlation(a, c) + 1.0) < 1e-10, "Pearson invertida = -1"
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-10, "Coseno identicas = 1"

    print("\n=== Todas las pruebas OK ===")
