# -*- coding: utf-8 -*-
"""
pdf_export.py - Generacion de reportes PDF con ReportLab.

Requerimiento R4.4: Exportacion de resultados a PDF.

Genera un documento profesional con:
  - Portada
  - Resumen del ETL
  - Tabla de clasificacion de riesgo
  - Resultados de patrones
  - Nota de algoritmos implementados

Usa ReportLab (libreria de bajo nivel para PDF), que esta permitida
por las restricciones del proyecto ya que no encapsula algoritmos
financieros ni de analisis de datos.
"""

import csv
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)

from algorithms.volatility import analyze_portfolio_risk
from algorithms.patterns import scan_patterns
from algorithms.similarity import compare_two_assets

DATA_CSV = os.path.join(_ROOT, "data", "dataset_maestro.csv")
OHLCV_FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def _load_data():
    """Carga dataset y extrae datos por activo."""
    rows = []
    with open(DATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    symbols = []
    for col in rows[0].keys():
        if col.endswith("_Close"):
            symbols.append(col.replace("_Close", ""))
    # Insertion sort
    for i in range(1, len(symbols)):
        cur = symbols[i]
        j = i - 1
        while j >= 0 and symbols[j] > cur:
            symbols[j + 1] = symbols[j]
            j -= 1
        symbols[j + 1] = cur

    return rows, symbols


def _get_series(rows, sym, field):
    col = sym + "_" + field
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


def generate_pdf(output_path=None):
    """
    Genera el reporte PDF completo.

    Parametros:
      output_path: str - ruta del archivo PDF de salida.
                   Si None, usa 'data/reporte_bursatil.pdf'.

    Retorno:
      str - ruta del archivo PDF generado.
    """
    if output_path is None:
        output_path = os.path.join(_ROOT, "data", "reporte_bursatil.pdf")

    # Asegurar directorio
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows, symbols = _load_data()
    n_rows = len(rows)
    n_symbols = len(symbols)
    date_range = ""
    if n_rows > 0:
        date_range = "{} a {}".format(
            rows[0].get("Date", "?"), rows[-1].get("Date", "?"))

    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=24, spaceAfter=20,
        textColor=colors.HexColor('#1a1d28'),
    )
    h1 = ParagraphStyle(
        'H1', parent=styles['Heading1'],
        fontSize=16, spaceBefore=20, spaceAfter=10,
        textColor=colors.HexColor('#1e2230'),
    )
    h2 = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontSize=13, spaceBefore=14, spaceAfter=8,
        textColor=colors.HexColor('#2d3348'),
    )
    body = styles['BodyText']
    body.fontSize = 10
    body.leading = 14

    # Construir documento
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    elements = []

    # ================================================================
    # PORTADA
    # ================================================================
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("Reporte Bursatil", title_style))
    elements.append(Paragraph("Analisis de Algoritmos - Dashboard Financiero", h2))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(HRFlowable(
        width="80%", thickness=2,
        color=colors.HexColor('#00d68f'), spaceAfter=20))

    cover_data = [
        ["Activos analizados", str(n_symbols)],
        ["Periodo", date_range],
        ["Registros por activo", str(n_rows)],
        ["Campos por activo", "OHLCV (Open, High, Low, Close, Volume)"],
        ["Fecha de generacion", time.strftime("%Y-%m-%d %H:%M")],
    ]
    cover_table = Table(cover_data, colWidths=[2.5 * inch, 4 * inch])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(cover_table)
    elements.append(PageBreak())

    # ================================================================
    # SECCION 1: RESUMEN DEL ETL
    # ================================================================
    elements.append(Paragraph("1. Resumen del Proceso ETL", h1))
    elements.append(Paragraph(
        "El pipeline ETL descarga datos financieros historicos de {} activos "
        "mediante peticiones HTTP directas a la API de Yahoo Finance (Chart API v8), "
        "sin utilizar librerias de alto nivel como yfinance o pandas_datareader. "
        "Los datos cubren el periodo {} ({} registros por activo).".format(
            n_symbols, date_range, n_rows), body))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Activos del portafolio:", h2))
    # Tabla de activos (4 columnas)
    asset_rows = []
    row = []
    for i, sym in enumerate(symbols):
        row.append(sym)
        if len(row) == 5:
            asset_rows.append(row)
            row = []
    if row:
        while len(row) < 5:
            row.append("")
        asset_rows.append(row)

    asset_table = Table(asset_rows, colWidths=[1.3 * inch] * 5)
    asset_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1d28')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4f8')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(asset_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Restricciones cumplidas:", h2))
    constraints = [
        "Sin yfinance, pandas_datareader ni pandas",
        "Descarga via urllib.request (HTTP directo)",
        "Sin datasets estaticos (datos generados en cada ejecucion)",
        "Todos los algoritmos implementados manualmente",
    ]
    for c in constraints:
        elements.append(Paragraph(
            u"\u2713 " + c, body))

    elements.append(PageBreak())

    # ================================================================
    # SECCION 2: CLASIFICACION DE RIESGO
    # ================================================================
    elements.append(Paragraph("2. Clasificacion de Riesgo", h1))
    elements.append(Paragraph(
        "La volatilidad historica anualizada se calcula como la desviacion estandar "
        "de los retornos logaritmicos diarios multiplicada por la raiz cuadrada de 252 "
        "(dias habiles por anio). Los activos se clasifican usando percentiles P33 y P66.",
        body))
    elements.append(Spacer(1, 10))

    # Calcular riesgo
    asset_prices = {}
    for sym in symbols:
        prices = _get_series(rows, sym, "Close")
        valid = [p for p in prices if p is not None]
        if len(valid) > 10:
            asset_prices[sym] = valid

    risk_result = analyze_portfolio_risk(asset_prices)

    elements.append(Paragraph(
        "Umbrales: P33 = {:.4f} ({:.1f}%), P66 = {:.4f} ({:.1f}%)".format(
            risk_result["thresholds"]["p33"],
            risk_result["thresholds"]["p33"] * 100,
            risk_result["thresholds"]["p66"],
            risk_result["thresholds"]["p66"] * 100,
        ), body))
    elements.append(Spacer(1, 10))

    # Tabla de clasificacion
    risk_header = ["#", "Activo", "Volatilidad", "%", "Categoria"]
    risk_data = [risk_header]
    for c in risk_result["classifications"]:
        risk_data.append([
            str(c["rank"]),
            c["symbol"],
            "{:.4f}".format(c["volatility"]),
            "{:.1f}%".format(c["volatility"] * 100),
            c["risk_class"],
        ])

    risk_table = Table(risk_data, colWidths=[
        0.5 * inch, 0.8 * inch, 1.2 * inch, 0.8 * inch, 1.5 * inch])
    risk_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e2230')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        # Body
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
    ]))

    # Color rows by risk class
    for i, c in enumerate(risk_result["classifications"], start=1):
        if c["risk_class"] == "Conservador":
            risk_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#00875a'))]))
        elif c["risk_class"] == "Moderado":
            risk_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#b8860b'))]))
        else:
            risk_table.setStyle(TableStyle([
                ('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#cc0033'))]))

    elements.append(risk_table)
    elements.append(Spacer(1, 15))

    summary = risk_result["summary"]
    elements.append(Paragraph(
        "Resumen: {} Conservador, {} Moderado, {} Agresivo".format(
            summary.get("Conservador", 0),
            summary.get("Moderado", 0),
            summary.get("Agresivo", 0)),
        body))

    elements.append(PageBreak())

    # ================================================================
    # SECCION 3: PATRONES DETECTADOS
    # ================================================================
    elements.append(Paragraph("3. Patrones Detectados (Sliding Window)", h1))
    elements.append(Paragraph(
        "Se aplica una ventana deslizante de 20 dias para detectar patrones "
        "en cada activo. Se analizan dos patrones formalizados:", body))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "<b>Patron 1 - Dias consecutivos al alza:</b> close[i] &gt; close[i-1]", body))
    elements.append(Paragraph(
        "<b>Patron 2 - Gap-up:</b> open[i] &gt; high[i-1]", body))
    elements.append(Spacer(1, 12))

    # Tabla de patrones para los primeros 10 activos
    pat_header = ["Activo", "Dias al alza", "Racha max", "Gap-ups", "Ventanas"]
    pat_data = [pat_header]
    for sym in symbols:
        closes = _get_series(rows, sym, "Close")
        opens_s = _get_series(rows, sym, "Open")
        highs_s = _get_series(rows, sym, "High")
        valid_c = [c if c is not None else 0 for c in closes]
        valid_o = [o if o is not None else 0 for o in opens_s]
        valid_h = [h if h is not None else 0 for h in highs_s]
        result = scan_patterns(valid_c, valid_o, valid_h, window_size=20)
        cu = result["consecutive_ups"]
        gu = result["gap_ups"]
        pat_data.append([
            sym,
            str(cu["total_ups"]),
            str(cu["max_streak"]),
            str(gu["total_gaps"]),
            str(cu["total_windows"]),
        ])

    pat_table = Table(pat_data, colWidths=[
        0.9 * inch, 1.1 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch])
    pat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e2230')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(pat_table)

    elements.append(PageBreak())

    # ================================================================
    # SECCION 4: ALGORITMOS IMPLEMENTADOS
    # ================================================================
    elements.append(Paragraph("4. Algoritmos Implementados", h1))
    elements.append(Paragraph(
        "Todos los algoritmos fueron implementados manualmente sin librerias "
        "de alto nivel (sin scipy, numpy, sklearn).", body))
    elements.append(Spacer(1, 10))

    algo_header = ["Algoritmo", "Tipo", "Complejidad T.", "Complejidad E."]
    algo_data = [algo_header]
    algos = [
        ["Distancia Euclidiana", "Similitud", "O(n)", "O(1)"],
        ["Correlacion de Pearson", "Similitud", "O(n)", "O(1)"],
        ["Dynamic Time Warping", "Similitud", "O(n*w)", "O(m)"],
        ["Similitud por Coseno", "Similitud", "O(n)", "O(1)"],
        ["Sliding Window (rachas)", "Patrones", "O(n*w)", "O(n)"],
        ["Sliding Window (gap-up)", "Patrones", "O(n)", "O(n)"],
        ["Volatilidad historica", "Riesgo", "O(n)", "O(n)"],
        ["Clasificacion de riesgo", "Riesgo", "O(k^2)", "O(k)"],
        ["Media movil simple (SMA)", "Tecnico", "O(n)", "O(n)"],
        ["Retornos logaritmicos", "Tecnico", "O(n)", "O(n)"],
    ]
    for a in algos:
        algo_data.append(a)

    algo_table = Table(algo_data, colWidths=[
        2.2 * inch, 1.0 * inch, 1.2 * inch, 1.2 * inch])
    algo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e2230')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
            colors.HexColor('#ffffff'), colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(algo_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Stack tecnologico:", h2))
    stack_items = [
        "Backend: Flask (Python)",
        "Frontend: HTML5 + CSS3 + JavaScript vanilla + Canvas API",
        "Graficos: Canvas API del navegador (sin Plotly, Chart.js ni Matplotlib)",
        "PDF: ReportLab (libreria de bajo nivel)",
        "Datos: CSV + dict/list nativos de Python (sin pandas)",
        "HTTP: urllib.request (sin yfinance)",
    ]
    for s in stack_items:
        elements.append(Paragraph(u"\u2022 " + s, body))

    # Build PDF
    doc.build(elements)
    return output_path


# ============================================================================
# Prueba directa
# ============================================================================

if __name__ == "__main__":
    print("Generando reporte PDF...")
    path = generate_pdf()
    print("PDF generado: {}".format(path))
    print("Tamano: {} bytes".format(os.path.getsize(path)))
