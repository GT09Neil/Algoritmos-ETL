/* ========================================================================
   dashboard.js — Canvas rendering for all charts (no external libs)
   Heatmap, Candlestick, Line chart, Bar chart — all manual Canvas API.
   ======================================================================== */

// ---- Color helpers ----
function heatColor(val) {
  // Divergent: red (-1) -> white (0) -> blue (+1)
  var r, g, b;
  if (val >= 0) {
    r = Math.round(255 * (1 - val));
    g = Math.round(255 * (1 - val * 0.4));
    b = 255;
  } else {
    var v = -val;
    r = 255;
    g = Math.round(255 * (1 - v * 0.4));
    b = Math.round(255 * (1 - v));
  }
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}

function riskColor(cls) {
  if (cls === 'Conservador') return '#00d68f';
  if (cls === 'Moderado') return '#fbbf24';
  return '#ff4d6a';
}

// ---- Heatmap ----
function loadHeatmap() {
  fetch('/api/heatmap').then(function(r){return r.json();}).then(function(data) {
    drawHeatmap(data.symbols, data.matrix);
  });
}

function drawHeatmap(symbols, matrix) {
  var canvas = document.getElementById('heatmap-canvas');
  if (!canvas) return;
  var n = symbols.length;
  var cellSize = 28;
  var labelW = 50;
  var w = labelW + n * cellSize;
  var h = labelW + n * cellSize;
  canvas.width = w;
  canvas.height = h;
  canvas.style.width = w + 'px';
  canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e2230';
  ctx.fillRect(0, 0, w, h);

  // Labels
  ctx.font = '9px Inter, sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (var i = 0; i < n; i++) {
    ctx.fillStyle = '#9aa0b0';
    ctx.fillText(symbols[i], labelW - 4, labelW + i * cellSize + cellSize / 2);
  }
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (var j = 0; j < n; j++) {
    ctx.save();
    ctx.translate(labelW + j * cellSize + cellSize / 2, labelW - 4);
    ctx.rotate(-Math.PI / 4);
    ctx.fillStyle = '#9aa0b0';
    ctx.fillText(symbols[j], 0, 0);
    ctx.restore();
  }

  // Cells
  for (var i = 0; i < n; i++) {
    for (var j = 0; j < n; j++) {
      var val = matrix[i][j];
      ctx.fillStyle = heatColor(val);
      ctx.fillRect(labelW + j * cellSize, labelW + i * cellSize, cellSize - 1, cellSize - 1);
      // Value text
      if (cellSize >= 24) {
        ctx.fillStyle = (Math.abs(val) > 0.5) ? '#fff' : '#333';
        ctx.font = '7px Inter';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(val.toFixed(2), labelW + j * cellSize + cellSize / 2, labelW + i * cellSize + cellSize / 2);
      }
    }
  }
}

// ---- Risk summary (dashboard) ----
function loadRiskSummary() {
  fetch('/api/risk').then(function(r){return r.json();}).then(function(data) {
    var el;
    el = document.getElementById('count-conservador');
    if (el) el.textContent = data.summary.Conservador || 0;
    el = document.getElementById('count-moderado');
    if (el) el.textContent = data.summary.Moderado || 0;
    el = document.getElementById('count-agresivo');
    if (el) el.textContent = data.summary.Agresivo || 0;
    drawRiskBars(data.classifications, 'risk-bars-canvas');
  });
}

function drawRiskBars(items, canvasId) {
  var canvas = document.getElementById(canvasId);
  if (!canvas) return;
  var n = items.length;
  var barH = 22;
  var gap = 4;
  var labelW = 55;
  var valW = 60;
  var w = canvas.parentElement.clientWidth || 500;
  var h = n * (barH + gap) + 20;
  canvas.width = w;
  canvas.height = h;
  canvas.style.width = '100%';
  canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);

  var maxVol = 0;
  for (var i = 0; i < n; i++) {
    if (items[i].volatility_pct > maxVol) maxVol = items[i].volatility_pct;
  }
  if (maxVol === 0) maxVol = 1;

  var barArea = w - labelW - valW - 20;

  for (var i = 0; i < n; i++) {
    var y = i * (barH + gap);
    var item = items[i];
    var bw = (item.volatility_pct / maxVol) * barArea;

    // Label
    ctx.fillStyle = '#9aa0b0';
    ctx.font = '11px Inter';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(item.symbol, labelW - 5, y + barH / 2);

    // Bar
    ctx.fillStyle = riskColor(item.risk_class);
    ctx.globalAlpha = 0.8;
    ctx.beginPath();
    ctx.roundRect(labelW, y, bw, barH, 4);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Value
    ctx.fillStyle = '#e8eaed';
    ctx.font = '10px Inter';
    ctx.textAlign = 'left';
    ctx.fillText(item.volatility_pct.toFixed(1) + '%', labelW + bw + 6, y + barH / 2);
  }
}

// ---- Candlestick ----
function loadCandlestick() {
  var symEl = document.getElementById('candle-symbol');
  var daysEl = document.getElementById('candle-days');
  if (!symEl) return;
  var sym = symEl.value;
  var days = daysEl ? daysEl.value : 250;
  fetch('/api/candlestick/' + sym + '?days=' + days)
    .then(function(r){return r.json();}).then(function(data) {
    drawCandlestick(data);
  });
}

function drawCandlestick(data) {
  var canvas = document.getElementById('candle-canvas');
  if (!canvas) return;
  var dates = data.dates;
  var n = dates.length;
  if (n === 0) return;

  var w = canvas.parentElement.clientWidth || 900;
  var h = 350;
  canvas.width = w;
  canvas.height = h;
  canvas.style.width = '100%';
  canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e2230';
  ctx.fillRect(0, 0, w, h);

  var padL = 60, padR = 20, padT = 20, padB = 40;
  var chartW = w - padL - padR;
  var chartH = h - padT - padB;

  // Find min/max
  var lo = Infinity, hi = -Infinity;
  for (var i = 0; i < n; i++) {
    var l = data.low[i], hh = data.high[i];
    if (l !== null && l < lo) lo = l;
    if (hh !== null && hh > hi) hi = hh;
  }
  var range = hi - lo;
  if (range === 0) range = 1;

  function yPos(v) { return padT + chartH - ((v - lo) / range) * chartH; }

  var candleW = Math.max(1, (chartW / n) - 1);

  // Grid lines
  ctx.strokeStyle = '#2d3348';
  ctx.lineWidth = 0.5;
  for (var g = 0; g < 5; g++) {
    var gy = padT + (chartH / 4) * g;
    ctx.beginPath();
    ctx.moveTo(padL, gy);
    ctx.lineTo(w - padR, gy);
    ctx.stroke();
    var gv = hi - (range / 4) * g;
    ctx.fillStyle = '#6b7280';
    ctx.font = '10px Inter';
    ctx.textAlign = 'right';
    ctx.fillText('$' + gv.toFixed(1), padL - 5, gy + 3);
  }

  // Candles
  for (var i = 0; i < n; i++) {
    var o = data.open[i], c = data.close[i], l = data.low[i], hh = data.high[i];
    if (o === null || c === null) continue;
    var x = padL + (i / n) * chartW;
    var bullish = c >= o;
    var color = bullish ? '#00d68f' : '#ff4d6a';

    // Wick
    if (l !== null && hh !== null) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + candleW / 2, yPos(hh));
      ctx.lineTo(x + candleW / 2, yPos(l));
      ctx.stroke();
    }

    // Body
    var yTop = yPos(Math.max(o, c));
    var yBot = yPos(Math.min(o, c));
    var bodyH = Math.max(1, yBot - yTop);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.9;
    ctx.fillRect(x, yTop, candleW, bodyH);
    ctx.globalAlpha = 1;
  }

  // SMA lines
  function drawSMA(smaArr, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    var started = false;
    for (var i = 0; i < n; i++) {
      var v = smaArr[i];
      if (v === null || v === undefined) continue;
      var x = padL + (i / n) * chartW + candleW / 2;
      var y = yPos(v);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  if (data.sma20) drawSMA(data.sma20, '#3b82f6');
  if (data.sma50) drawSMA(data.sma50, '#a78bfa');

  // Date labels
  ctx.fillStyle = '#6b7280';
  ctx.font = '9px Inter';
  ctx.textAlign = 'center';
  var labelStep = Math.max(1, Math.floor(n / 8));
  for (var i = 0; i < n; i += labelStep) {
    var x = padL + (i / n) * chartW + candleW / 2;
    ctx.fillText(dates[i], x, h - 10);
  }
}

// ---- Similarity ----
function runSimilarity() {
  var a = document.getElementById('sim-sym-a').value;
  var b = document.getElementById('sim-sym-b').value;
  document.getElementById('sim-loading').style.display = 'block';
  document.getElementById('sim-results').style.display = 'none';

  fetch('/api/similarity?a=' + a + '&b=' + b)
    .then(function(r){return r.json();}).then(function(data) {
    document.getElementById('sim-loading').style.display = 'none';
    document.getElementById('sim-results').style.display = 'block';

    var m = data.metrics;
    document.getElementById('m-euclidean').textContent = m.euclidean.toFixed(4);
    document.getElementById('m-pearson').textContent = m.pearson.toFixed(4);
    document.getElementById('m-dtw').textContent = m.dtw.toFixed(4);
    document.getElementById('m-cosine').textContent = m.cosine.toFixed(4);
    document.getElementById('sim-info').textContent = m.n_points + ' puntos | ' + data.time_seconds + 's';

    // Color code pearson
    var pEl = document.getElementById('m-pearson');
    pEl.style.color = m.pearson > 0.7 ? '#00d68f' : m.pearson > 0.3 ? '#fbbf24' : '#ff4d6a';
    var cEl = document.getElementById('m-cosine');
    cEl.style.color = m.cosine > 0.7 ? '#00d68f' : m.cosine > 0.3 ? '#fbbf24' : '#ff4d6a';

    drawLineChart(data);
  });
}

function drawLineChart(data) {
  var canvas = document.getElementById('sim-chart-canvas');
  if (!canvas) return;
  var dates = data.chart.dates;
  var sa = data.chart.series_a;
  var sb = data.chart.series_b;
  var n = dates.length;

  var w = canvas.parentElement.clientWidth || 800;
  var h = 300;
  canvas.width = w;
  canvas.height = h;
  canvas.style.width = '100%';
  canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e2230';
  ctx.fillRect(0, 0, w, h);

  var padL = 60, padR = 60, padT = 20, padB = 40;
  var cw = w - padL - padR, ch = h - padT - padB;

  // Normalize both to 0-1
  function normalize(arr) {
    var lo = Infinity, hi = -Infinity;
    for (var i = 0; i < arr.length; i++) {
      if (arr[i] !== null) {
        if (arr[i] < lo) lo = arr[i];
        if (arr[i] > hi) hi = arr[i];
      }
    }
    var r = hi - lo || 1;
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      out.push(arr[i] !== null ? (arr[i] - lo) / r : null);
    }
    return out;
  }
  var na = normalize(sa), nb = normalize(sb);

  function drawLine(arr, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    var started = false;
    for (var i = 0; i < n; i++) {
      if (arr[i] === null) continue;
      var x = padL + (i / n) * cw;
      var y = padT + ch - arr[i] * ch;
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  drawLine(na, '#3b82f6');
  drawLine(nb, '#ff4d6a');

  // Legend
  ctx.fillStyle = '#3b82f6';
  ctx.fillRect(padL, h - 15, 12, 3);
  ctx.fillStyle = '#9aa0b0';
  ctx.font = '10px Inter';
  ctx.textAlign = 'left';
  ctx.fillText(data.symbol_a, padL + 16, h - 10);
  ctx.fillStyle = '#ff4d6a';
  ctx.fillRect(padL + 80, h - 15, 12, 3);
  ctx.fillStyle = '#9aa0b0';
  ctx.fillText(data.symbol_b, padL + 96, h - 10);
}

// ---- Patterns ----
function loadPatterns() {
  var sym = document.getElementById('pat-symbol').value;
  var win = document.getElementById('pat-window').value;
  document.getElementById('pat-loading').style.display = 'block';
  document.getElementById('pat-results').style.display = 'none';

  fetch('/api/patterns/' + sym + '?window=' + win)
    .then(function(r){return r.json();}).then(function(data) {
    document.getElementById('pat-loading').style.display = 'none';
    document.getElementById('pat-results').style.display = 'block';

    var cu = data.consecutive_ups;
    document.getElementById('pat-total-ups').textContent = cu.total_ups;
    document.getElementById('pat-max-streak').textContent = cu.max_streak;
    document.getElementById('pat-windows').textContent = cu.total_windows;

    var gu = data.gap_ups;
    document.getElementById('pat-total-gaps').textContent = gu.total_gaps;
    document.getElementById('pat-max-gaps-win').textContent = gu.max_gaps_in_window;
    document.getElementById('pat-win-size').textContent = gu.window_size;

    drawStreakChart(cu.streak_freq);
  });
}

function drawStreakChart(freq) {
  var canvas = document.getElementById('streak-chart-canvas');
  if (!canvas) return;

  // Sort keys
  var keys = [];
  for (var k in freq) keys.push(parseInt(k));
  // Insertion sort
  for (var i = 1; i < keys.length; i++) {
    var cur = keys[i], j = i - 1;
    while (j >= 0 && keys[j] > cur) { keys[j + 1] = keys[j]; j--; }
    keys[j + 1] = cur;
  }

  var n = keys.length;
  if (n === 0) return;

  var w = canvas.parentElement.clientWidth || 400;
  var h = 200;
  canvas.width = w;
  canvas.height = h;
  canvas.style.width = '100%';
  canvas.style.height = h + 'px';
  var ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1e2230';
  ctx.fillRect(0, 0, w, h);

  var padL = 50, padR = 10, padT = 10, padB = 30;
  var cw = w - padL - padR, ch = h - padT - padB;

  var maxVal = 0;
  for (var i = 0; i < n; i++) {
    if (freq[keys[i]] > maxVal) maxVal = freq[keys[i]];
  }
  if (maxVal === 0) maxVal = 1;

  var barW = Math.max(8, (cw / n) - 6);

  for (var i = 0; i < n; i++) {
    var val = freq[keys[i]];
    var bh = (val / maxVal) * ch;
    var x = padL + (i / n) * cw + 3;
    var y = padT + ch - bh;

    var grad = ctx.createLinearGradient(x, y, x, padT + ch);
    grad.addColorStop(0, '#3b82f6');
    grad.addColorStop(1, '#1e3a5f');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, bh, 3);
    ctx.fill();

    // Value label
    ctx.fillStyle = '#e8eaed';
    ctx.font = '9px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(val, x + barW / 2, y - 4);

    // X label
    ctx.fillStyle = '#9aa0b0';
    ctx.fillText(keys[i] + 'd', x + barW / 2, h - 8);
  }
}

// ---- Risk page ----
function loadRiskPage() {
  fetch('/api/risk').then(function(r){return r.json();}).then(function(data) {
    var el;
    el = document.getElementById('rc-conservador');
    if (el) el.textContent = data.summary.Conservador || 0;
    el = document.getElementById('rc-moderado');
    if (el) el.textContent = data.summary.Moderado || 0;
    el = document.getElementById('rc-agresivo');
    if (el) el.textContent = data.summary.Agresivo || 0;

    drawRiskBars(data.classifications, 'vol-bars-canvas');

    // Table
    var tbody = document.getElementById('risk-tbody');
    if (tbody) {
      tbody.innerHTML = '';
      for (var i = 0; i < data.classifications.length; i++) {
        var c = data.classifications[i];
        var cls = c.risk_class.toLowerCase();
        var tr = document.createElement('tr');
        tr.innerHTML = '<td>' + c.rank + '</td><td><strong>' + c.symbol + '</strong></td>'
          + '<td>' + c.volatility.toFixed(4) + '</td>'
          + '<td>' + c.volatility_pct.toFixed(1) + '%</td>'
          + '<td><span class="tag tag-' + cls + '">' + c.risk_class + '</span></td>';
        tbody.appendChild(tr);
      }
    }
  });
}
