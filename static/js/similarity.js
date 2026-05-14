/* similarity.js — Interactive per-algorithm visualizations */
var _simData = null;
var _activeAlgo = null;

function runSimilarity() {
  var a = document.getElementById('sim-sym-a').value;
  var b = document.getElementById('sim-sym-b').value;
  document.getElementById('sim-loading').style.display = 'block';
  document.getElementById('sim-results').style.display = 'none';
  _activeAlgo = null;

  fetch('/api/similarity?a=' + a + '&b=' + b)
    .then(function(r){return r.json();}).then(function(data) {
    _simData = data;
    document.getElementById('sim-loading').style.display = 'none';
    document.getElementById('sim-results').style.display = 'block';

    var m = data.metrics;
    document.getElementById('m-euclidean').textContent = m.euclidean.toFixed(4);
    document.getElementById('m-pearson').textContent = m.pearson.toFixed(4);
    document.getElementById('m-dtw').textContent = m.dtw.toFixed(4);
    document.getElementById('m-cosine').textContent = m.cosine.toFixed(4);
    document.getElementById('sim-info').textContent = m.n_points + ' puntos | ' + data.time_seconds + 's';

    var pEl = document.getElementById('m-pearson');
    pEl.style.color = m.pearson > 0.7 ? '#00d68f' : m.pearson > 0.3 ? '#fbbf24' : '#ff4d6a';
    var cEl = document.getElementById('m-cosine');
    cEl.style.color = m.cosine > 0.7 ? '#00d68f' : m.cosine > 0.3 ? '#fbbf24' : '#ff4d6a';

    clearActiveCards();
    drawOverviewChart(data);
    document.getElementById('algo-explanation').style.display = 'none';
  });
}

function clearActiveCards() {
  var cards = document.querySelectorAll('.sim-metric-card');
  for (var i = 0; i < cards.length; i++) cards[i].classList.remove('active');
}

function selectAlgorithm(algo) {
  if (!_simData) return;
  _activeAlgo = algo;
  clearActiveCards();
  var card = document.getElementById('card-' + algo);
  if (card) card.classList.add('active');
  document.getElementById('algo-explanation').style.display = 'block';

  if (algo === 'euclidean') { drawEuclidean(_simData); showExplanation('euclidean'); }
  else if (algo === 'pearson') { drawPearson(_simData); showExplanation('pearson'); }
  else if (algo === 'dtw') { drawDTW(_simData); showExplanation('dtw'); }
  else if (algo === 'cosine') { drawCosine(_simData); showExplanation('cosine'); }
}

// ---- Helpers ----
function getCtx(canvasId, parentW) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return null;
  var w = parentW || canvas.parentElement.clientWidth || 800;
  var h = 350;
  canvas.width = w; canvas.height = h;
  canvas.style.width = '100%'; canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e2230'; ctx.fillRect(0, 0, w, h);
  return ctx;
}

function norm01(arr) {
  var lo = Infinity, hi = -Infinity;
  for (var i = 0; i < arr.length; i++) { if (arr[i] !== null) { if (arr[i] < lo) lo = arr[i]; if (arr[i] > hi) hi = arr[i]; } }
  var r = hi - lo || 1, out = [];
  for (var i = 0; i < arr.length; i++) out.push(arr[i] !== null ? (arr[i] - lo) / r : null);
  return out;
}

function drawLineSeries(ctx, arr, color, n, padL, padT, cw, ch, lw) {
  ctx.strokeStyle = color; ctx.lineWidth = lw || 2; ctx.beginPath();
  var started = false;
  for (var i = 0; i < n; i++) {
    if (arr[i] === null || arr[i] === undefined) continue;
    var x = padL + (i / n) * cw, y = padT + ch - arr[i] * ch;
    if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

/**
 * Draws year labels on the X axis based on the dates array.
 * dates: array of date strings (e.g. "2020-01-15")
 * n: total number of data points
 * ctx: canvas 2d context
 * padL, padT, cw, ch: chart area geometry
 * yLabel: Y position for the labels (typically padT + ch + offset)
 */
function drawYearLabels(ctx, dates, n, padL, cw, yLabel) {
  if (!dates || dates.length === 0) return;
  ctx.fillStyle = '#9aa0b0'; ctx.font = '10px Inter'; ctx.textAlign = 'center';
  var lastYear = '';
  for (var i = 0; i < dates.length; i++) {
    var d = dates[i];
    if (!d) continue;
    var year = d.substring(0, 4);
    if (year !== lastYear) {
      lastYear = year;
      var x = padL + (i / n) * cw;
      // Draw a small tick
      ctx.strokeStyle = '#3d4460'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, yLabel - 12); ctx.lineTo(x, yLabel - 6); ctx.stroke();
      ctx.fillStyle = '#9aa0b0';
      ctx.fillText(year, x, yLabel);
    }
  }
}

// ---- Overview Chart ----
function drawOverviewChart(data) {
  document.getElementById('viz-title').textContent = 'Series Temporales — Vista General';
  var canvas = document.getElementById('sim-chart-canvas');
  if (!canvas) return;
  var ctx = getCtx('sim-chart-canvas');
  if (!ctx) return;
  var sa = data.chart.series_a, sb = data.chart.series_b, n = sa.length;
  var na = norm01(sa), nb = norm01(sb);
  var padL = 50, padR = 50, padT = 20, padB = 55, w = canvas.width, h = canvas.height;
  var cw = w - padL - padR, ch = h - padT - padB;
  drawLineSeries(ctx, na, '#3b82f6', n, padL, padT, cw, ch);
  drawLineSeries(ctx, nb, '#ff4d6a', n, padL, padT, cw, ch);
  // Year labels on X axis
  drawYearLabels(ctx, data.chart.dates, n, padL, cw, padT + ch + 18);
  // Legend
  ctx.fillStyle = '#3b82f6'; ctx.fillRect(padL, h - 18, 14, 4);
  ctx.fillStyle = '#9aa0b0'; ctx.font = '11px Inter'; ctx.textAlign = 'left';
  ctx.fillText(data.symbol_a, padL + 18, h - 12);
  ctx.fillStyle = '#ff4d6a'; ctx.fillRect(padL + 90, h - 18, 14, 4);
  ctx.fillStyle = '#9aa0b0'; ctx.fillText(data.symbol_b, padL + 108, h - 12);
}

// ---- 1. Euclidean ----
function drawEuclidean(data) {
  document.getElementById('viz-title').textContent = 'Distancia Euclidiana — Diferencias Punto a Punto';
  var canvas = document.getElementById('sim-chart-canvas');
  var ctx = getCtx('sim-chart-canvas'); if (!ctx) return;
  var ra = data.extra.returns_a, rb = data.extra.returns_b, diffs = data.extra.point_diffs;
  var n = ra.length; if (n === 0) return;
  var w = canvas.width, h = canvas.height;
  var padL = 50, padR = 20, padT = 30, padB = 55;
  var cw = w - padL - padR, ch = h - padT - padB;

  // Normalize returns together
  var allVals = ra.concat(rb);
  var lo = Infinity, hi = -Infinity;
  for (var i = 0; i < allVals.length; i++) { if (allVals[i] < lo) lo = allVals[i]; if (allVals[i] > hi) hi = allVals[i]; }
  var range = hi - lo || 1;
  function yPos(v) { return padT + ch - ((v - lo) / range) * ch; }

  // Draw difference bars
  for (var i = 0; i < n; i++) {
    var x = padL + (i / n) * cw;
    var ya = yPos(ra[i]), yb = yPos(rb[i]);
    var absDiff = Math.abs(diffs[i]);
    var maxDiff = 0;
    for (var k = 0; k < diffs.length; k++) if (Math.abs(diffs[k]) > maxDiff) maxDiff = Math.abs(diffs[k]);
    var alpha = 0.15 + (absDiff / (maxDiff || 1)) * 0.6;
    ctx.strokeStyle = 'rgba(251,191,36,' + alpha + ')';
    ctx.lineWidth = 1; ctx.beginPath();
    ctx.moveTo(x, ya); ctx.lineTo(x, yb); ctx.stroke();
  }

  // Draw lines
  var na = [], nb2 = [];
  for (var i = 0; i < n; i++) { na.push((ra[i] - lo) / range); nb2.push((rb[i] - lo) / range); }
  drawLineSeries(ctx, na, '#3b82f6', n, padL, padT, cw, ch, 2);
  drawLineSeries(ctx, nb2, '#ff4d6a', n, padL, padT, cw, ch, 2);

  // Year labels on X axis
  drawYearLabels(ctx, data.extra.returns_dates, n, padL, cw, padT + ch + 18);

  // Title label
  ctx.fillStyle = '#e8eaed'; ctx.font = 'bold 11px Inter'; ctx.textAlign = 'left';
  ctx.fillText('Líneas amarillas = distancia en cada punto', padL, padT - 10);
  // Legend
  ctx.fillStyle = '#3b82f6'; ctx.fillRect(padL, h - 15, 12, 3);
  ctx.fillStyle = '#9aa0b0'; ctx.font = '10px Inter'; ctx.fillText(data.symbol_a, padL + 16, h - 10);
  ctx.fillStyle = '#ff4d6a'; ctx.fillRect(padL + 80, h - 15, 12, 3);
  ctx.fillStyle = '#9aa0b0'; ctx.fillText(data.symbol_b, padL + 96, h - 10);
  ctx.fillStyle = '#fbbf24'; ctx.fillRect(padL + 160, h - 15, 12, 3);
  ctx.fillStyle = '#9aa0b0'; ctx.fillText('Distancia', padL + 176, h - 10);
}

// ---- 2. Pearson ----
function drawPearson(data) {
  document.getElementById('viz-title').textContent = 'Correlación de Pearson — Scatter Plot';
  var canvas = document.getElementById('sim-chart-canvas');
  var ctx = getCtx('sim-chart-canvas'); if (!ctx) return;
  var ra = data.extra.returns_a, rb = data.extra.returns_b;
  var n = ra.length; if (n === 0) return;
  var w = canvas.width, h = canvas.height;
  var pad = 60, cw = w - pad * 2, ch = h - pad * 2;

  // Find ranges
  var loA = Infinity, hiA = -Infinity, loB = Infinity, hiB = -Infinity;
  for (var i = 0; i < n; i++) {
    if (ra[i] < loA) loA = ra[i]; if (ra[i] > hiA) hiA = ra[i];
    if (rb[i] < loB) loB = rb[i]; if (rb[i] > hiB) hiB = rb[i];
  }
  var rngA = hiA - loA || 1, rngB = hiB - loB || 1;
  function xPos(v) { return pad + ((v - loA) / rngA) * cw; }
  function yPos(v) { return pad + ch - ((v - loB) / rngB) * ch; }

  // Grid
  ctx.strokeStyle = '#2d3348'; ctx.lineWidth = 0.5;
  for (var g = 0; g <= 4; g++) {
    var gy = pad + (ch / 4) * g;
    ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(pad + cw, gy); ctx.stroke();
    var gx = pad + (cw / 4) * g;
    ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, pad + ch); ctx.stroke();
  }

  // Linear regression line
  var sumA = 0, sumB = 0, sumAB = 0, sumA2 = 0;
  for (var i = 0; i < n; i++) { sumA += ra[i]; sumB += rb[i]; sumAB += ra[i]*rb[i]; sumA2 += ra[i]*ra[i]; }
  var meanA = sumA/n, meanB = sumB/n;
  var denom = sumA2 - n*meanA*meanA;
  if (Math.abs(denom) > 1e-15) {
    var slope = (sumAB - n*meanA*meanB) / denom;
    var intercept = meanB - slope * meanA;
    ctx.strokeStyle = 'rgba(0,214,143,0.7)'; ctx.lineWidth = 2; ctx.setLineDash([6,4]);
    ctx.beginPath();
    ctx.moveTo(xPos(loA), yPos(slope * loA + intercept));
    ctx.lineTo(xPos(hiA), yPos(slope * hiA + intercept));
    ctx.stroke(); ctx.setLineDash([]);
  }

  // Points
  for (var i = 0; i < n; i++) {
    var px = xPos(ra[i]), py = yPos(rb[i]);
    ctx.beginPath(); ctx.arc(px, py, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(59,130,246,0.6)'; ctx.fill();
  }

  // Axis labels
  ctx.fillStyle = '#9aa0b0'; ctx.font = '11px Inter'; ctx.textAlign = 'center';
  ctx.fillText('Retornos ' + data.symbol_a, pad + cw/2, h - 10);
  ctx.save(); ctx.translate(15, pad + ch/2); ctx.rotate(-Math.PI/2);
  ctx.fillText('Retornos ' + data.symbol_b, 0, 0); ctx.restore();

  // Pearson value
  var pearson = data.metrics.pearson;
  var pColor = pearson > 0.7 ? '#00d68f' : pearson > 0.3 ? '#fbbf24' : '#ff4d6a';
  ctx.fillStyle = pColor; ctx.font = 'bold 14px Inter'; ctx.textAlign = 'right';
  ctx.fillText('r = ' + pearson.toFixed(4), w - pad, pad - 10);
  // Trend label
  ctx.fillStyle = '#00d68f'; ctx.font = '10px Inter';
  ctx.fillText('— Línea de tendencia', w - pad, pad + 15);
}

// ---- 3. DTW ----
function drawDTW(data) {
  document.getElementById('viz-title').textContent = 'DTW — Alineación Dinámica Temporal';
  var canvas = document.getElementById('sim-chart-canvas');
  var ctx = getCtx('sim-chart-canvas'); if (!ctx) return;
  var sa = data.extra.dtw_series_a, sb = data.extra.dtw_series_b, path = data.extra.dtw_path;
  var n = sa.length, m = sb.length;
  if (n === 0 || m === 0) return;
  var w = canvas.width, h = canvas.height;
  var padL = 50, padR = 20, padT = 30, padB = 45;
  var cw = w - padL - padR;
  var halfH = (h - padT - padB) / 2 - 15;

  // Normalize
  var nsa = norm01(sa), nsb = norm01(sb);

  // Draw series A (top)
  var yOffA = padT;
  ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2; ctx.beginPath();
  for (var i = 0; i < n; i++) {
    var x = padL + (i / n) * cw, y = yOffA + halfH - nsa[i] * halfH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Draw series B (bottom)
  var yOffB = padT + halfH + 30;
  ctx.strokeStyle = '#ff4d6a'; ctx.lineWidth = 2; ctx.beginPath();
  for (var i = 0; i < m; i++) {
    var x = padL + (i / m) * cw, y = yOffB + halfH - nsb[i] * halfH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Draw warping connections
  if (path && path.length > 0) {
    ctx.strokeStyle = 'rgba(167,139,250,0.35)'; ctx.lineWidth = 1;
    for (var k = 0; k < path.length; k++) {
      var pi = path[k][0], pj = path[k][1];
      if (pi >= n || pj >= m) continue;
      var x1 = padL + (pi / n) * cw, y1 = yOffA + halfH - nsa[pi] * halfH;
      var x2 = padL + (pj / m) * cw, y2 = yOffB + halfH - nsb[pj] * halfH;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    }
  }

  // Year labels on X axis (below series B)
  var dtwDates = data.extra.dtw_dates;
  drawYearLabels(ctx, dtwDates, n, padL, cw, yOffB + halfH + 18);

  // Labels
  ctx.fillStyle = '#3b82f6'; ctx.font = 'bold 11px Inter'; ctx.textAlign = 'left';
  ctx.fillText(data.symbol_a + ' (serie original)', padL, yOffA - 5);
  ctx.fillStyle = '#ff4d6a';
  ctx.fillText(data.symbol_b + ' (serie comparada)', padL, yOffB - 5);
  ctx.fillStyle = '#a78bfa'; ctx.font = '10px Inter';
  ctx.fillText('Líneas violeta = alineación DTW', padL + 250, yOffA - 5);
}

// ---- 4. Cosine ----
function drawCosine(data) {
  document.getElementById('viz-title').textContent = 'Similitud Coseno — Dirección Vectorial';
  var canvas = document.getElementById('sim-chart-canvas');
  var ctx = getCtx('sim-chart-canvas'); if (!ctx) return;
  var w = canvas.width, h = canvas.height;
  var cx = w / 2, cy = h / 2 + 10;
  var radius = Math.min(w, h) / 2 - 60;

  var cosVal = data.metrics.cosine;
  var angle = Math.acos(Math.max(-1, Math.min(1, cosVal)));

  // Draw arc background
  ctx.strokeStyle = '#2d3348'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, radius * 0.6, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(cx, cy, radius * 0.3, 0, Math.PI * 2); ctx.stroke();

  // Vector A (horizontal right)
  var vecAx = cx + radius * 0.9, vecAy = cy;
  ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(vecAx, vecAy); ctx.stroke();
  // Arrowhead
  ctx.fillStyle = '#3b82f6'; ctx.beginPath();
  ctx.moveTo(vecAx, vecAy); ctx.lineTo(vecAx - 10, vecAy - 5); ctx.lineTo(vecAx - 10, vecAy + 5); ctx.fill();

  // Vector B (at angle)
  var vecBx = cx + radius * 0.9 * Math.cos(-angle);
  var vecBy = cy + radius * 0.9 * Math.sin(-angle);
  ctx.strokeStyle = '#ff4d6a'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(vecBx, vecBy); ctx.stroke();
  ctx.fillStyle = '#ff4d6a'; ctx.beginPath();
  var arrAngle = Math.atan2(vecBy - cy, vecBx - cx);
  ctx.moveTo(vecBx, vecBy);
  ctx.lineTo(vecBx - 10 * Math.cos(arrAngle - 0.3), vecBy - 10 * Math.sin(arrAngle - 0.3));
  ctx.lineTo(vecBx - 10 * Math.cos(arrAngle + 0.3), vecBy - 10 * Math.sin(arrAngle + 0.3));
  ctx.fill();

  // Draw angle arc
  ctx.strokeStyle = 'rgba(0,214,143,0.7)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(cx, cy, radius * 0.35, -angle, 0); ctx.stroke();

  // Angle label
  var angleDeg = (angle * 180 / Math.PI).toFixed(1);
  var labelAngle = -angle / 2;
  ctx.fillStyle = '#00d68f'; ctx.font = 'bold 14px Inter'; ctx.textAlign = 'center';
  ctx.fillText('θ = ' + angleDeg + '°', cx + radius * 0.45 * Math.cos(labelAngle), cy + radius * 0.45 * Math.sin(labelAngle));

  // Labels
  ctx.fillStyle = '#3b82f6'; ctx.font = 'bold 12px Inter'; ctx.textAlign = 'left';
  ctx.fillText('Vector ' + data.symbol_a, vecAx + 10, vecAy - 5);
  ctx.fillStyle = '#ff4d6a';
  ctx.fillText('Vector ' + data.symbol_b, vecBx + 10, vecBy - 5);

  // Cosine value
  var cColor = cosVal > 0.7 ? '#00d68f' : cosVal > 0.3 ? '#fbbf24' : '#ff4d6a';
  ctx.fillStyle = cColor; ctx.font = 'bold 16px Inter'; ctx.textAlign = 'center';
  ctx.fillText('cos(θ) = ' + cosVal.toFixed(4), cx, padT = 25);

  // Norms info
  ctx.fillStyle = '#9aa0b0'; ctx.font = '11px Inter';
  ctx.fillText('||A|| = ' + data.extra.cosine_norm_a.toFixed(4) + '    ||B|| = ' + data.extra.cosine_norm_b.toFixed(4), cx, h - 15);
  ctx.fillText('A · B = ' + data.extra.cosine_dot.toFixed(6), cx, h - 35);
}

// ---- Explanations ----
var EXPLANATIONS = {
  euclidean: {
    formula: '<div class="formula-box"><span class="formula-title">Fórmula Matemática</span><code>d(x, y) = √( Σ (xᵢ - yᵢ)² )</code></div>',
    interpret: '<div class="interpret-box"><span class="interpret-title">Interpretación</span><p>La <strong>distancia euclidiana</strong> mide la distancia "en línea recta" entre dos series en un espacio n-dimensional.</p><ul><li><strong>d = 0</strong>: Series idénticas</li><li><strong>d → ∞</strong>: Series muy diferentes</li></ul><p>Las barras amarillas muestran la diferencia punto a punto. Mayor intensidad = mayor discrepancia local.</p><p><strong>Complejidad:</strong> O(n) tiempo, O(1) espacio</p></div>'
  },
  pearson: {
    formula: '<div class="formula-box"><span class="formula-title">Fórmula Matemática</span><code>r = Σ(xᵢ - x̄)(yᵢ - ȳ) / √(Σ(xᵢ - x̄)² · Σ(yᵢ - ȳ)²)</code></div>',
    interpret: '<div class="interpret-box"><span class="interpret-title">Interpretación Financiera</span><p>La <strong>correlación de Pearson</strong> mide la relación lineal entre los retornos de dos activos.</p><ul><li><strong>r ≈ +1</strong>: Se mueven en la misma dirección (alta correlación positiva)</li><li><strong>r ≈ 0</strong>: Sin relación lineal (diversificación ideal)</li><li><strong>r ≈ -1</strong>: Se mueven en direcciones opuestas (cobertura natural)</li></ul><p>El scatter plot muestra cada par de retornos. La línea verde es la tendencia lineal.</p><p><strong>Complejidad:</strong> O(n) tiempo, O(1) espacio</p></div>'
  },
  dtw: {
    formula: '<div class="formula-box"><span class="formula-title">Fórmula Recursiva</span><code>DTW[i][j] = |a[i] - b[j]| + min(DTW[i-1][j], DTW[i][j-1], DTW[i-1][j-1])</code></div>',
    interpret: '<div class="interpret-box"><span class="interpret-title">Interpretación</span><p><strong>Dynamic Time Warping</strong> encuentra la alineación óptima entre series permitiendo deformaciones temporales.</p><ul><li>Las líneas violeta conectan puntos alineados</li><li>Permite detectar patrones similares <em>desfasados en el tiempo</em></li><li><strong>DTW = 0</strong>: Alineación perfecta</li></ul><p>A diferencia de Euclidiana, DTW tolera diferencias de velocidad. Ideal para patrones financieros que se repiten con retardo.</p><p><strong>Complejidad:</strong> O(n·w) tiempo con banda Sakoe-Chiba</p></div>'
  },
  cosine: {
    formula: '<div class="formula-box"><span class="formula-title">Fórmula Matemática</span><code>cos(θ) = (A · B) / (||A|| · ||B||)</code></div>',
    interpret: '<div class="interpret-box"><span class="interpret-title">Interpretación</span><p>La <strong>similitud coseno</strong> mide el ángulo entre dos vectores, ignorando su magnitud.</p><ul><li><strong>cos(θ) = 1</strong>: Misma dirección (patrones idénticos)</li><li><strong>cos(θ) = 0</strong>: Ortogonales (sin relación)</li><li><strong>cos(θ) = -1</strong>: Dirección opuesta</li></ul><p>Ideal para comparar la <em>forma</em> de los movimientos sin importar la amplitud. Dos activos pueden tener rendimientos muy distintos pero moverse en la misma "dirección".</p><p><strong>Complejidad:</strong> O(n) tiempo, O(1) espacio</p></div>'
  }
};

function showExplanation(algo) {
  var exp = EXPLANATIONS[algo];
  if (!exp) return;
  document.getElementById('algo-formula').innerHTML = exp.formula;
  document.getElementById('algo-interpret').innerHTML = exp.interpret;
}
