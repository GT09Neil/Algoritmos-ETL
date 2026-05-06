# Declaración de Uso de Inteligencia Artificial Generativa

**Proyecto:** AlgoFinance — Dashboard Bursátil  
**Curso:** Análisis de Algoritmos, 2026-1  
**Universidad del Quindío**

---

## 1. Herramientas Utilizadas

Se utilizó un asistente de IA generativa como herramienta de apoyo durante
el desarrollo del proyecto. Su rol fue estrictamente de soporte técnico, no
de sustitución del diseño algorítmico.

## 2. Tareas en las que se Usó IA

| Tarea | Tipo de uso | Validación humana |
|-------|------------|-------------------|
| Generación de boilerplate (Flask routes, HTML templates) | Aceleración de escritura | Revisión y ajuste manual |
| Estructuración de docstrings con fórmulas matemáticas | Formato y redacción | Verificación de fórmulas contra fuentes académicas |
| Sugerencias de diseño CSS | Estética visual | Ajuste manual de colores y layout |
| Depuración de errores (encoding Windows, rutas) | Diagnóstico | Validación con ejecución real |

## 3. Tareas Realizadas sin IA

| Tarea | Justificación |
|-------|---------------|
| Diseño algorítmico de similitud (Euclidiana, Pearson, DTW, Coseno) | Comprensión requerida por el curso |
| Elección de estructuras de datos (list, dict) | Decisión fundamentada en complejidad |
| Análisis de complejidad temporal y espacial | Razonamiento formal propio |
| Diseño del pipeline ETL | Arquitectura definida según requerimientos |
| Optimización de DTW (Sakoe-Chiba + 2 filas) | Investigación académica propia |
| Definición de patrones financieros (gap-up) | Conocimiento de dominio aplicado |
| Clasificación de riesgo por percentiles | Diseño estadístico propio |

## 4. Validación Independiente

Todos los algoritmos fueron verificados de forma independiente:

- **Euclidiana:** Verificación manual con vectores simples (distancia identica = 0).
- **Pearson:** Comprobación contra propiedades conocidas (r=1 para series idénticas, r=-1 para invertidas).
- **DTW:** Validación de que DTW(a,a) = 0 y DTW(a,b) > 0 para series distintas.
- **Coseno:** Verificación de ortogonalidad y normalización.
- **Datos reales:** VOO vs SPY (Pearson=0.997) confirma que ambos rastrean el S&P 500.
- **Riesgo:** EFA (19%) Conservador, PBR (49%) Agresivo — coherente con la realidad financiera.

## 5. Compromiso

El uso de IA generativa **no sustituyó** la comprensión ni el análisis formal
de los algoritmos. Cada algoritmo implementado puede ser explicado y defendido
en detalle durante la sustentación, incluyendo su formulación matemática,
comportamiento asintótico y justificación de estructuras de datos.
