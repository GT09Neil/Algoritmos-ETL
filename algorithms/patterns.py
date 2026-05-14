# -*- coding: utf-8 -*-
"""
patterns.py - Deteccion de patrones en series de tiempo mediante ventana deslizante.

Requerimiento 3 (parte 1): implementar un algoritmo basado en sliding window
que recorra el historial de precios y detecte la frecuencia de patrones
previamente definidos.

RESTRICCION: NO se usa pandas, numpy, scipy ni funciones de alto nivel.
Solo estructuras basicas de Python (list, dict) y math.

Patrones implementados:
  1. Dias consecutivos al alza (close[i] > close[i-1])
  2. Gap-up (open[i] > high[i-1]) — patron adicional formalizado

Cada patron incluye:
  - Definicion formal
  - Algoritmo con pseudocodigo
  - Analisis de complejidad
  - Interpretacion financiera
"""


# ============================================================================
# 1. Patron: Dias consecutivos al alza
# ============================================================================

def detect_consecutive_ups(closes, window_size=20):
    """
    Detecta secuencias de dias consecutivos al alza usando ventana deslizante.

    Definicion formal del patron:
      Una racha al alza de longitud k comenzando en posicion i existe si:
        close[i+j] > close[i+j-1]  para todo j en {1, 2, ..., k}
      donde k >= 1 (al menos un dia de subida respecto al anterior).

    Algoritmo (sliding window):
      Entrada: closes = [c_0, c_1, ..., c_{n-1}], window_size = w
      Salida: dict con:
        - "streak_freq": dict {longitud_racha: frecuencia_total}
        - "windows": list de dict por ventana con info de rachas
        - "max_streak": longitud de la racha mas larga encontrada
        - "total_ups": total de dias individuales al alza

      Preprocesamiento — crear array binario de subidas:
        ups[i] = 1 si closes[i] > closes[i-1], 0 en caso contrario
        (para i = 1..n-1; ups[0] no se define)

      Recorrido con ventana deslizante:
        para cada posicion de inicio s en 0..n-w:
          ventana = ups[s..s+w-1]
          recorrer la ventana contando rachas de 1s consecutivos
          registrar la longitud de cada racha encontrada

      Complejidad: O(n * w) en el peor caso. Si w es constante, O(n).
                   En la practica w << n (tipicamente w=20, n=1758).

    Parametros:
      closes: list[float] — precios de cierre ordenados cronologicamente.
      window_size: int — tamano de la ventana deslizante (default 20 dias).

    Retorno:
      dict con keys:
        "streak_freq": {int: int} — frecuencia de rachas por longitud
        "max_streak": int — racha mas larga encontrada
        "total_ups": int — total de dias al alza
        "total_windows": int — numero de ventanas analizadas
        "window_size": int — tamano de ventana usado

    Complejidad temporal: O(n * w) peor caso, O(n) si w constante.
    Complejidad espacial: O(n) para el array de subidas + O(k) para frecuencias
                          donde k = numero de longitudes distintas de racha.
    """
    # Basicamente esta funcion detecta patrones de dias consecutivos al alza
    # en una serie de tiempo. Es decir, si una serie sube, la otra tambien
    # sube?

    n = len(closes)
    if n < 2:
        return {
            "streak_freq": {},
            "max_streak": 0,
            "total_ups": 0,
            "total_windows": 0,
            "window_size": window_size,
        }

    # Paso 1: crear array binario de subidas — O(n)
    ups = []
    ups.append(0)  # posicion 0 no tiene anterior
    total_ups = 0
    for i in range(1, n):
        if closes[i] is not None and closes[i - 1] is not None:
            # Si el precio de cierre del dia actual es mayor que el del dia anterior
            # Entonces se agrega un 1 a la lista de ups
            if closes[i] > closes[i - 1]:
                ups.append(1)
                total_ups += 1
            else:
                # Si no, se agrega un 0
                ups.append(0)
        else:
            # Si alguno de los precios es None, se agrega un 0
            ups.append(0)

    # Paso 2: recorrer con ventana deslizante y contar rachas
    streak_freq = {}  # {longitud: frecuencia}
    max_streak = 0
    total_windows = 0

    # Asegurar ventana valida
    w = window_size
    if w > n:
        w = n
    if w < 2:
        w = 2

    for start in range(n - w + 1):
        total_windows += 1
        # Contar rachas dentro de la ventana [start, start+w-1]
        current_streak = 0
        for j in range(start, start + w):
            if ups[j] == 1:
                current_streak += 1
            else:
                if current_streak > 0:
                    # Registrar racha terminada
                    if current_streak not in streak_freq:
                        streak_freq[current_streak] = 0
                    streak_freq[current_streak] += 1
                    if current_streak > max_streak:
                        max_streak = current_streak
                current_streak = 0
        # Racha al final de la ventana
        if current_streak > 0:
            if current_streak not in streak_freq:
                streak_freq[current_streak] = 0
            streak_freq[current_streak] += 1
            if current_streak > max_streak:
                max_streak = current_streak

    return {
        "streak_freq": streak_freq,
        "max_streak": max_streak,
        "total_ups": total_ups,
        "total_windows": total_windows,
        "window_size": w,
    }


# ============================================================================
# 2. Patron: Gap-Up
# ============================================================================

def detect_gap_ups(opens, highs, window_size=20):
    """
    Detecta patrones de gap-up usando ventana deslizante.

    Definicion formal del patron:
      Un gap-up en el dia i existe si:
        open[i] > high[i-1]
      Es decir, el precio de apertura del dia supera el maximo del dia anterior.
      Esto indica que hubo un salto alcista significativo entre el cierre y la
      apertura, frecuentemente causado por noticias o eventos fuera de horario.

    Significado financiero:
      - Senal de impulso alcista fuerte.
      - Frecuente antes de rallies sostenidos.
      - Su frecuencia puede indicar periodos de alta actividad especulativa.

    Algoritmo (sliding window):
      Entrada: opens = [o_0, ..., o_{n-1}], highs = [h_0, ..., h_{n-1}], w
      Salida: dict con conteo de gap-ups por ventana y total.

      Preprocesamiento:
        gaps[i] = 1 si open[i] > high[i-1], 0 en caso contrario (i >= 1)

      Recorrido optimizado (acumulador deslizante):
        1. Contar gap-ups en la primera ventana [0..w-1]: sum(gaps[0..w-1])
        2. Para cada posicion subsiguiente:
           - Sumar gaps[start+w] (nuevo elemento que entra)
           - Restar gaps[start] (elemento que sale)
        Esto da O(n) en lugar de O(n*w).

    Parametros:
      opens: list[float] — precios de apertura.
      highs: list[float] — precios maximos del dia.
      window_size: int — tamano de la ventana.

    Retorno:
      dict con keys:
        "total_gaps": int — total de gap-ups detectados
        "gap_positions": list[int] — indices donde ocurren gap-ups
        "gaps_per_window": list[int] — conteo de gap-ups en cada ventana
        "max_gaps_in_window": int — maximo de gap-ups en una sola ventana
        "window_size": int

    Complejidad temporal: O(n) con acumulador deslizante.
    Complejidad espacial: O(n) para el array de gaps y la lista de resultados.
    """

    # Basicamente esta funcion detecta patrones de gap-up
    # en una serie de tiempo. Es decir, si una serie sube, la otra tambien
    # sube?

    # Es parecido al anterior, solo que este no utiliza binario y compara directamente
    # respecto al día anterior.
    n = len(opens)
    if n < 2 or len(highs) < 2:
        return {
            "total_gaps": 0,
            "gap_positions": [],
            "gaps_per_window": [],
            "max_gaps_in_window": 0,
            "window_size": window_size,
        }

    n = min(len(opens), len(highs))

    # Paso 1: crear array binario de gap-ups — O(n)
    gaps = []
    gaps.append(0)  # posicion 0 no tiene anterior
    total_gaps = 0
    gap_positions = []
    for i in range(1, n):
        if (opens[i] is not None and highs[i - 1] is not None
                and opens[i] > highs[i - 1]):
            gaps.append(1)
            total_gaps += 1
            gap_positions.append(i)
        else:
            gaps.append(0)

    # Paso 2: acumulador deslizante — O(n)
    w = window_size
    if w > n:
        w = n
    if w < 2:
        w = 2

    # Suma de la primera ventana
    window_sum = 0
    for i in range(w):
        window_sum += gaps[i]

    gaps_per_window = []
    gaps_per_window.append(window_sum)
    max_gaps_in_window = window_sum

    # Deslizar
    for start in range(1, n - w + 1):
        window_sum += gaps[start + w - 1]  # entra el nuevo
        window_sum -= gaps[start - 1]       # sale el viejo
        gaps_per_window.append(window_sum)
        if window_sum > max_gaps_in_window:
            max_gaps_in_window = window_sum

    return {
        "total_gaps": total_gaps,
        "gap_positions": gap_positions,
        "gaps_per_window": gaps_per_window,
        "max_gaps_in_window": max_gaps_in_window,
        "window_size": w,
    }


# ============================================================================
# Funcion consolidada
# ============================================================================

def scan_patterns(closes, opens, highs, window_size=20):
    """
    Ejecuta todos los detectores de patrones sobre las series de un activo.

    Parametros:
      closes: list[float] — precios de cierre.
      opens: list[float] — precios de apertura.
      highs: list[float] — precios maximos.
      window_size: int — tamano de ventana deslizante.

    Retorno:
      dict con keys:
        "consecutive_ups": resultado de detect_consecutive_ups
        "gap_ups": resultado de detect_gap_ups

    Complejidad temporal: O(n * w) para rachas + O(n) para gaps = O(n * w).
    Complejidad espacial: O(n).
    """
    return {
        "consecutive_ups": detect_consecutive_ups(closes, window_size),
        "gap_ups": detect_gap_ups(opens, highs, window_size),
    }


# ============================================================================
# Pruebas rapidas
# ============================================================================

if __name__ == "__main__":
    print("=== Pruebas de patterns.py ===\n")

    # Datos de prueba: 15 dias
    closes = [100, 102, 103, 101, 104, 105, 106, 103, 107, 108, 109, 110, 108, 111, 112]
    opens  = [99,  101, 102, 103, 100, 104, 105, 107, 102, 106, 108, 109, 111, 107, 110]
    highs  = [101, 103, 104, 104, 105, 106, 107, 108, 108, 109, 110, 111, 112, 112, 113]

    # Test 1: Rachas al alza
    result_ups = detect_consecutive_ups(closes, window_size=5)
    print("Rachas al alza (ventana=5):")
    print("  Frecuencia de rachas:", result_ups["streak_freq"])
    print("  Racha mas larga:", result_ups["max_streak"])
    print("  Total dias al alza:", result_ups["total_ups"])
    print("  Ventanas analizadas:", result_ups["total_windows"])

    # Test 2: Gap-ups
    result_gaps = detect_gap_ups(opens, highs, window_size=5)
    print("\nGap-ups (ventana=5):")
    print("  Total gap-ups:", result_gaps["total_gaps"])
    print("  Posiciones:", result_gaps["gap_positions"])
    print("  Max en una ventana:", result_gaps["max_gaps_in_window"])

    # Test 3: Consolidado
    result_all = scan_patterns(closes, opens, highs, window_size=5)
    print("\nPatrones consolidados OK")
    print("  Keys:", list(result_all.keys()))

    print("\n=== Todas las pruebas OK ===")
