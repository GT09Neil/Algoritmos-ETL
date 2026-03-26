# -*- coding: utf-8 -*-
"""
sorting.py - Implementaciones manuales de 12 algoritmos de ordenamiento.

RESTRICCIÓN CRÍTICA: NO se usa list.sort(), sorted(), heapq, ni ninguna
función de biblioteca que encapsule un algoritmo de ordenamiento.

Cada algoritmo:
  - Recibe una lista y la ordena (in-place o retornando copia según convenga).
  - Documenta complejidad temporal y espacial.
  - Soporta un parámetro `key` opcional para extraer el valor de comparación.

Algoritmos implementados (12):
  1. TimSort (manual: runs + merge con galloping)
  2. Comb Sort
  3. Selection Sort
  4. Tree Sort (BST)
  5. Pigeonhole Sort
  6. Bucket Sort
  7. QuickSort (mediana de 3)
  8. HeapSort
  9. Bitonic Sort
  10. Gnome Sort
  11. Binary Insertion Sort
  12. Radix Sort (LSD)
"""


# ============================================================================
# Registro de algoritmos disponibles
# ============================================================================

ALGORITHMS = {}


def _register(name):
    """Decorador que registra un algoritmo en el diccionario ALGORITHMS."""
    def decorator(fn):
        ALGORITHMS[name] = fn
        return fn
    return decorator


def run_sort(algorithm_name, data, key=None):
    """
    Ejecuta un algoritmo de ordenamiento por nombre.
    Retorna la lista ordenada (puede ser la misma referencia o una nueva).
    """
    if algorithm_name not in ALGORITHMS:
        raise ValueError("Algoritmo '{}' no registrado. Disponibles: {}".format(
            algorithm_name, list(ALGORITHMS.keys())))
    return ALGORITHMS[algorithm_name](data, key=key)


# ============================================================================
# Utilidades internas
# ============================================================================

def _key_val(item, key):
    """Extrae el valor de comparación de un elemento."""
    if key is None:
        return item
    return key(item)


# ============================================================================
# 1. TimSort (manual)
# ============================================================================
# Complejidad temporal: O(n log n) promedio y peor caso.
# Complejidad espacial: O(n) para el merge temporal.
# Algoritmo híbrido: divide en runs (subsecuencias ordenadas), usa insertion
# sort para runs pequeños, y merge para combinarlos.
# ============================================================================

_MIN_RUN = 32


def _insertion_sort_range(arr, left, right, key):
    """Insertion sort sobre arr[left..right] inclusive. O(n^2) peor caso."""
    for i in range(left + 1, right + 1):
        current = arr[i]
        current_key = _key_val(current, key)
        j = i - 1
        while j >= left and _key_val(arr[j], key) > current_key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = current


def _merge(arr, left, mid, right, key):
    """Merge de arr[left..mid] y arr[mid+1..right]. O(n) tiempo y espacio."""
    left_part = []
    right_part = []
    for i in range(left, mid + 1):
        left_part.append(arr[i])
    for i in range(mid + 1, right + 1):
        right_part.append(arr[i])

    i = 0
    j = 0
    k = left
    while i < len(left_part) and j < len(right_part):
        if _key_val(left_part[i], key) <= _key_val(right_part[j], key):
            arr[k] = left_part[i]
            i += 1
        else:
            arr[k] = right_part[j]
            j += 1
        k += 1
    while i < len(left_part):
        arr[k] = left_part[i]
        i += 1
        k += 1
    while j < len(right_part):
        arr[k] = right_part[j]
        j += 1
        k += 1


def _calc_min_run(n):
    """Calcula el tamaño mínimo de run para TimSort."""
    r = 0
    while n >= _MIN_RUN:
        r |= n & 1
        n >>= 1
    return n + r


@_register("TimSort")
def tim_sort(arr, key=None):
    """
    TimSort manual. Identifica runs naturales, extiende con insertion sort,
    y los combina con merge iterativo.
    Complejidad: O(n log n) tiempo, O(n) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    min_run = _calc_min_run(n)

    # Fase 1: crear runs con insertion sort
    for start in range(0, n, min_run):
        end = start + min_run - 1
        if end >= n:
            end = n - 1
        _insertion_sort_range(arr, start, end, key)

    # Fase 2: merge iterativo de runs
    size = min_run
    while size < n:
        for left in range(0, n, 2 * size):
            mid = left + size - 1
            right = left + 2 * size - 1
            if right >= n:
                right = n - 1
            if mid < right:
                _merge(arr, left, mid, right, key)
        size *= 2

    return arr


# ============================================================================
# 2. Comb Sort
# ============================================================================
# Complejidad temporal: O(n^2 / 2^p) promedio, O(n^2) peor caso.
# Complejidad espacial: O(1).
# Mejora de Bubble Sort: usa un gap decreciente (factor 1.3).
# ============================================================================

@_register("Comb Sort")
def comb_sort(arr, key=None):
    """
    Comb Sort: bubble sort con gap decreciente.
    Complejidad: O(n^2/2^p) promedio, O(n^2) peor caso, O(1) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    gap = n
    shrink = 1.3
    is_sorted = False

    while not is_sorted:
        gap = int(gap / shrink)
        if gap <= 1:
            gap = 1
            is_sorted = True

        i = 0
        while i + gap < n:
            if _key_val(arr[i], key) > _key_val(arr[i + gap], key):
                arr[i], arr[i + gap] = arr[i + gap], arr[i]
                is_sorted = False
            i += 1

    return arr


# ============================================================================
# 3. Selection Sort
# ============================================================================
# Complejidad temporal: O(n^2) siempre.
# Complejidad espacial: O(1).
# Selecciona el mínimo en cada pasada y lo coloca en su posición.
# ============================================================================

@_register("Selection Sort")
def selection_sort(arr, key=None):
    """
    Selection Sort clásico.
    Complejidad: O(n^2) tiempo, O(1) espacio.
    """
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if _key_val(arr[j], key) < _key_val(arr[min_idx], key):
                min_idx = j
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr


# ============================================================================
# 4. Tree Sort (BST)
# ============================================================================
# Complejidad temporal: O(n log n) promedio, O(n^2) peor caso (datos ordenados).
# Complejidad espacial: O(n) para el árbol.
# Inserta todos los elementos en un BST y hace recorrido inorden.
# ============================================================================

class _BSTNode:
    """Nodo de un árbol binario de búsqueda."""
    __slots__ = ('val', 'item', 'left', 'right')

    def __init__(self, val, item):
        self.val = val      # valor de comparación (key)
        self.item = item    # elemento original
        self.left = None
        self.right = None


def _bst_insert(root, val, item):
    """Inserta un elemento en el BST iterativamente. Retorna la raiz."""
    new_node = _BSTNode(val, item)
    if root is None:
        return new_node
    current = root
    while True:
        if val < current.val:
            if current.left is None:
                current.left = new_node
                return root
            current = current.left
        else:
            if current.right is None:
                current.right = new_node
                return root
            current = current.right


def _bst_inorder(node, result):
    """Recorrido inorden iterativo para evitar desbordamiento de pila."""
    stack = []
    current = node
    while current is not None or len(stack) > 0:
        while current is not None:
            stack.append(current)
            current = current.left
        current = stack.pop()
        result.append(current.item)
        current = current.right


@_register("Tree Sort")
def tree_sort(arr, key=None):
    """
    Tree Sort: inserta en BST y hace recorrido inorden.
    Complejidad: O(n log n) promedio, O(n^2) peor caso, O(n) espacio.
    NOTA: Para datos ya ordenados el BST se degrada a lista enlazada.
    Se usa recorrido iterativo para evitar RecursionError en listas grandes.
    """
    n = len(arr)
    if n <= 1:
        return arr

    root = None
    for item in arr:
        val = _key_val(item, key)
        root = _bst_insert(root, val, item)

    result = []
    _bst_inorder(root, result)

    for i in range(n):
        arr[i] = result[i]
    return arr


# ============================================================================
# 5. Pigeonhole Sort
# ============================================================================
# Complejidad temporal: O(n + rango).
# Complejidad espacial: O(rango).
# Para enteros; con floats se multiplica por 100 (centavos).
# ============================================================================

@_register("Pigeonhole Sort")
def pigeonhole_sort(arr, key=None):
    """
    Pigeonhole Sort: distribución directa por valor.
    Para floats: se convierte a centavos (×100, redondeado a entero).
    Complejidad: O(n + rango) tiempo, O(rango) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Extraer valores. Si son floats (tienen parte fraccionaria) se convierten
    # a centavos (×100). Si la key ya retorna enteros, se usan directamente.
    raw_vals = []
    has_fraction = False
    for item in arr:
        v = _key_val(item, key)
        raw_vals.append(v)
        if not has_fraction and v != int(v):
            has_fraction = True

    int_vals = []
    if has_fraction:
        for v in raw_vals:
            int_vals.append(int(round(v * 100)))
    else:
        for v in raw_vals:
            int_vals.append(int(round(v)))

    min_val = int_vals[0]
    max_val = int_vals[0]
    for v in int_vals:
        if v < min_val:
            min_val = v
        if v > max_val:
            max_val = v

    rng = max_val - min_val + 1

    # Proteccion: si el rango es demasiado grande, usar bucket sort interno
    if rng > 300_000_000:
        # Fallback: distribuir en buckets proporcionales y usar insertion sort
        num_buckets = int(n ** 0.5)
        if num_buckets < 1:
            num_buckets = 1
        buckets = []
        for _ in range(num_buckets):
            buckets.append([])
        value_range = max_val - min_val
        for i in range(n):
            idx = int((int_vals[i] - min_val) / value_range * (num_buckets - 1))
            buckets[idx].append(arr[i])
        for bkt in buckets:
            blen = len(bkt)
            for bi in range(1, blen):
                cur = bkt[bi]
                cur_key = _key_val(cur, key)
                bj = bi - 1
                while bj >= 0 and _key_val(bkt[bj], key) > cur_key:
                    bkt[bj + 1] = bkt[bj]
                    bj -= 1
                bkt[bj + 1] = cur
        pos = 0
        for bkt in buckets:
            for item in bkt:
                arr[pos] = item
                pos += 1
        return arr

    # Crear pigeonholes
    holes = []
    for _ in range(rng):
        holes.append([])

    for i in range(n):
        idx = int_vals[i] - min_val
        holes[idx].append(arr[i])

    # Reconstruir array
    pos = 0
    for hole in holes:
        for item in hole:
            arr[pos] = item
            pos += 1

    return arr


# ============================================================================
# 6. Bucket Sort
# ============================================================================
# Complejidad temporal: O(n + k) promedio, O(n^2) peor caso.
# Complejidad espacial: O(n + k) donde k = número de buckets.
# Usa insertion sort dentro de cada bucket.
# ============================================================================

@_register("Bucket Sort")
def bucket_sort(arr, key=None):
    """
    Bucket Sort: distribuye en buckets y ordena cada uno con insertion sort.
    Complejidad: O(n + k) promedio, O(n^2) peor caso, O(n + k) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Encontrar rango de valores
    vals = []
    for item in arr:
        vals.append(_key_val(item, key))

    min_val = vals[0]
    max_val = vals[0]
    for v in vals:
        if v < min_val:
            min_val = v
        if v > max_val:
            max_val = v

    if max_val == min_val:
        return arr  # todos iguales

    # Número de buckets: raíz cuadrada de n
    num_buckets = int(n ** 0.5)
    if num_buckets < 1:
        num_buckets = 1

    buckets = []
    for _ in range(num_buckets):
        buckets.append([])

    # Distribuir en buckets
    value_range = max_val - min_val
    for i in range(n):
        idx = int((vals[i] - min_val) / value_range * (num_buckets - 1))
        buckets[idx].append(arr[i])

    # Ordenar cada bucket con insertion sort
    for bucket in buckets:
        blen = len(bucket)
        for i in range(1, blen):
            current = bucket[i]
            current_key = _key_val(current, key)
            j = i - 1
            while j >= 0 and _key_val(bucket[j], key) > current_key:
                bucket[j + 1] = bucket[j]
                j -= 1
            bucket[j + 1] = current

    # Reconstruir
    pos = 0
    for bucket in buckets:
        for item in bucket:
            arr[pos] = item
            pos += 1

    return arr


# ============================================================================
# 7. QuickSort (mediana de 3)
# ============================================================================
# Complejidad temporal: O(n log n) promedio, O(n^2) peor caso.
# Complejidad espacial: O(log n) para la pila de recursión.
# Pivot: mediana de 3 (primero, medio, último) para mitigar peor caso.
# Implementación iterativa para evitar stack overflow en listas grandes.
# ============================================================================

@_register("QuickSort")
def quick_sort(arr, key=None):
    """
    QuickSort iterativo con pivot mediana-de-3.
    Para subarrays pequeños (<=10) usa insertion sort.
    Complejidad: O(n log n) promedio, O(n^2) peor caso, O(log n) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Pila: pares (low, high)
    stack = [(0, n - 1)]

    while len(stack) > 0:
        low, high = stack.pop()
        if low >= high:
            continue

        # Subarrays pequeños: insertion sort directo
        if high - low <= 10:
            _insertion_sort_range(arr, low, high, key)
            continue

        # Mediana de 3 como pivot
        mid = (low + high) // 2

        # Ordenar los tres: arr[low], arr[mid], arr[high]
        if _key_val(arr[low], key) > _key_val(arr[mid], key):
            arr[low], arr[mid] = arr[mid], arr[low]
        if _key_val(arr[low], key) > _key_val(arr[high], key):
            arr[low], arr[high] = arr[high], arr[low]
        if _key_val(arr[mid], key) > _key_val(arr[high], key):
            arr[mid], arr[high] = arr[high], arr[mid]

        # Pivot es la mediana (arr[mid]); moverlo a high-1
        arr[mid], arr[high - 1] = arr[high - 1], arr[mid]
        pivot_val = _key_val(arr[high - 1], key)

        # Partición con dos punteros
        i = low + 1
        j = high - 2
        while True:
            while _key_val(arr[i], key) < pivot_val:
                i += 1
            while _key_val(arr[j], key) > pivot_val:
                j -= 1
            if i >= j:
                break
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
            j -= 1

        # Colocar pivot en posición final
        arr[i], arr[high - 1] = arr[high - 1], arr[i]

        stack.append((low, i - 1))
        stack.append((i + 1, high))

    return arr


# ============================================================================
# 8. HeapSort
# ============================================================================
# Complejidad temporal: O(n log n) siempre.
# Complejidad espacial: O(1) (in-place).
# Construye un max-heap y extrae el máximo repetidamente.
# ============================================================================

def _sift_down(arr, n, i, key):
    """Hundir el nodo i en un max-heap de tamaño n. O(log n)."""
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2

    if left < n and _key_val(arr[left], key) > _key_val(arr[largest], key):
        largest = left
    if right < n and _key_val(arr[right], key) > _key_val(arr[largest], key):
        largest = right

    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        _sift_down(arr, n, largest, key)


@_register("HeapSort")
def heap_sort(arr, key=None):
    """
    HeapSort in-place.
    Complejidad: O(n log n) tiempo, O(1) espacio (sin contar la pila de sift_down).
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Construir max-heap (bottom-up)
    for i in range(n // 2 - 1, -1, -1):
        _sift_down(arr, n, i, key)

    # Extraer máximo repetidamente
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        _sift_down(arr, i, 0, key)

    return arr


# ============================================================================
# 9. Bitonic Sort
# ============================================================================
# Complejidad temporal: O(n log^2 n).
# Complejidad espacial: O(1) (in-place).
# Red de ordenamiento: requiere que n sea potencia de 2 (se hace padding).
# ============================================================================

_BITONIC_SENTINEL = object()

def _bitonic_compare(arr, i, j, ascending, key):
    """Compara e intercambia arr[i] y arr[j] según dirección. Maneja padding sentinel."""
    item_i = arr[i]
    item_j = arr[j]
    
    # Manejo optimizado del centinela (infinito positivo)
    if item_i is _BITONIC_SENTINEL and item_j is _BITONIC_SENTINEL:
        return
    elif item_i is _BITONIC_SENTINEL:
        if ascending:
            arr[i], arr[j] = arr[j], arr[i]
        return
    elif item_j is _BITONIC_SENTINEL:
        if not ascending:
            arr[i], arr[j] = arr[j], arr[i]
        return

    val_i = _key_val(item_i, key)
    val_j = _key_val(item_j, key)
    if ascending:
        if val_i > val_j:
            arr[i], arr[j] = arr[j], arr[i]
    else:
        if val_i < val_j:
            arr[i], arr[j] = arr[j], arr[i]


def _bitonic_merge(arr, low, cnt, ascending, key):
    """Merge bitónico iterativo."""
    if cnt <= 1:
        return
    k = 1
    while k < cnt:
        k *= 2
    k = k // 2
    for i in range(low, low + cnt - k):
        _bitonic_compare(arr, i, i + k, ascending, key)
    _bitonic_merge(arr, low, k, ascending, key)
    _bitonic_merge(arr, low + k, cnt - k, ascending, key)


def _bitonic_sort_rec(arr, low, cnt, ascending, key):
    """Bitonic sort recursivo."""
    if cnt <= 1:
        return
    mid = cnt // 2
    _bitonic_sort_rec(arr, low, mid, True, key)
    _bitonic_sort_rec(arr, low + mid, cnt - mid, False, key)
    _bitonic_merge(arr, low, cnt, ascending, key)


@_register("Bitonic Sort")
def bitonic_sort(arr, key=None):
    """
    Bitonic Sort. Si n no es potencia de 2, se hace padding con float('inf')
    y se eliminan al final.
    Complejidad: O(n log^2 n) tiempo, O(1) espacio extra (sin padding).
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Calcular potencia de 2 >= n
    padded_n = 1
    while padded_n < n:
        padded_n *= 2

    # Padding
    padding_count = padded_n - n
    for _ in range(padding_count):
        arr.append(_BITONIC_SENTINEL)

    _bitonic_sort_rec(arr, 0, padded_n, True, key)

    # Eliminar padding
    while len(arr) > n:
        arr.pop()

    return arr


# ============================================================================
# 10. Gnome Sort
# ============================================================================
# Complejidad temporal: O(n^2) peor caso.
# Complejidad espacial: O(1).
# Variante de insertion sort; avanza y retrocede como un gnomo.
# ============================================================================

@_register("Gnome Sort")
def gnome_sort(arr, key=None):
    """
    Gnome Sort: avanza si está bien, retrocede para insertar.
    Complejidad: O(n^2) tiempo, O(1) espacio.
    """
    n = len(arr)
    idx = 0
    while idx < n:
        if idx == 0:
            idx += 1
        elif _key_val(arr[idx], key) >= _key_val(arr[idx - 1], key):
            idx += 1
        else:
            arr[idx], arr[idx - 1] = arr[idx - 1], arr[idx]
            idx -= 1
    return arr


# ============================================================================
# 11. Binary Insertion Sort
# ============================================================================
# Complejidad temporal: O(n^2) debido a los shifts (O(n log n) comparaciones).
# Complejidad espacial: O(1).
# Usa búsqueda binaria para encontrar la posición de inserción.
# ============================================================================

def _binary_search_insert_pos(arr, item_key, low, high, key):
    """Encuentra la posición de inserción con búsqueda binaria. O(log n)."""
    while low < high:
        mid = (low + high) // 2
        if _key_val(arr[mid], key) <= item_key:
            low = mid + 1
        else:
            high = mid
    return low


@_register("Binary Insertion Sort")
def binary_insertion_sort(arr, key=None):
    """
    Binary Insertion Sort: insertion sort con búsqueda binaria.
    Complejidad: O(n^2) tiempo (O(n log n) comparaciones + O(n^2) shifts),
                 O(1) espacio.
    """
    n = len(arr)
    for i in range(1, n):
        current = arr[i]
        current_key = _key_val(current, key)
        pos = _binary_search_insert_pos(arr, current_key, 0, i, key)
        # Shift: mover elementos a la derecha
        j = i
        while j > pos:
            arr[j] = arr[j - 1]
            j -= 1
        arr[pos] = current
    return arr


# ============================================================================
# 12. Radix Sort (LSD - Least Significant Digit)
# ============================================================================
# Complejidad temporal: O(d * n) donde d = número de dígitos.
# Complejidad espacial: O(n + b) donde b = base (10).
# Para floats: se convierte a centavos (enteros) para procesar por dígitos.
# Maneja negativos separando en dos grupos.
# ============================================================================

def _counting_sort_by_digit(items, int_vals, exp, base=10):
    """Counting sort estable por un dígito específico (exp). O(n + base)."""
    n = len(items)
    output_items = [None] * n
    output_vals = [0] * n
    count = [0] * base

    for i in range(n):
        digit = (int_vals[i] // exp) % base
        count[digit] += 1

    for i in range(1, base):
        count[i] += count[i - 1]

    # Recorrer de derecha a izquierda para estabilidad
    for i in range(n - 1, -1, -1):
        digit = (int_vals[i] // exp) % base
        count[digit] -= 1
        pos = count[digit]
        output_items[pos] = items[i]
        output_vals[pos] = int_vals[i]

    for i in range(n):
        items[i] = output_items[i]
        int_vals[i] = output_vals[i]


@_register("Radix Sort")
def radix_sort(arr, key=None):
    """
    Radix Sort LSD para floats (convertidos a centavos/enteros).
    Maneja negativos: ordena negativos y positivos por separado y concatena.
    Complejidad: O(d * n) tiempo, O(n + b) espacio.
    """
    n = len(arr)
    if n <= 1:
        return arr

    # Detectar si los valores son floats (tienen parte fraccionaria)
    raw_vals = []
    has_fraction = False
    for item in arr:
        v = _key_val(item, key)
        raw_vals.append(v)
        if not has_fraction and v != int(v):
            has_fraction = True

    neg_items = []
    neg_vals = []
    pos_items = []
    pos_vals = []

    for i in range(len(raw_vals)):
        v = raw_vals[i]
        if has_fraction:
            int_v = int(round(v * 100))
        else:
            int_v = int(round(v))
        if int_v < 0:
            neg_items.append(arr[i])
            neg_vals.append(-int_v)  # trabajar con absoluto
        else:
            pos_items.append(arr[i])
            pos_vals.append(int_v)

    # Radix sort de positivos
    if len(pos_items) > 0:
        max_val = pos_vals[0]
        for v in pos_vals:
            if v > max_val:
                max_val = v
        exp = 1
        while max_val // exp > 0:
            _counting_sort_by_digit(pos_items, pos_vals, exp)
            exp *= 10

    # Radix sort de negativos (por absoluto, luego invertir)
    if len(neg_items) > 0:
        max_val = neg_vals[0]
        for v in neg_vals:
            if v > max_val:
                max_val = v
        exp = 1
        while max_val // exp > 0:
            _counting_sort_by_digit(neg_items, neg_vals, exp)
            exp *= 10
        # Invertir negativos (el mayor absoluto es el menor negativo)
        # Inversión manual (sin list.reverse())
        left_idx = 0
        right_idx = len(neg_items) - 1
        while left_idx < right_idx:
            neg_items[left_idx], neg_items[right_idx] = neg_items[right_idx], neg_items[left_idx]
            left_idx += 1
            right_idx -= 1

    # Reconstruir: negativos primero (ya invertidos), luego positivos
    pos = 0
    for item in neg_items:
        arr[pos] = item
        pos += 1
    for item in pos_items:
        arr[pos] = item
        pos += 1

    return arr


# ============================================================================
# Pruebas rápidas (punto de entrada directo)
# ============================================================================

if __name__ == "__main__":
    import random

    print("=== Pruebas de algoritmos de ordenamiento ===\n")
    test_data = [random.uniform(-100, 1000) for _ in range(200)]
    expected = list(test_data)
    # Ordenar con método manual simple para comparación (bubble sort)
    for i in range(len(expected)):
        for j in range(i + 1, len(expected)):
            if expected[i] > expected[j]:
                expected[i], expected[j] = expected[j], expected[i]

    all_pass = True
    for name, func in ALGORITHMS.items():
        test_copy = list(test_data)
        result = func(test_copy, key=None)
        ok = True
        for i in range(len(expected)):
            if abs(result[i] - expected[i]) > 1e-9:
                ok = False
                break
        status = "OK" if ok else "FAIL"
        if not ok:
            all_pass = False
        print("  {:25s} -> {}".format(name, status))

    print("\n{} pruebas completadas.".format(
        "Todas" if all_pass else "ALGUNAS FALLARON"))
