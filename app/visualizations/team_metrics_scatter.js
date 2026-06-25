/**
 * CREACIÓN DE UN SCATTER DE STATS DE EQUIPO CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Colores del equipo de interés, similares, resto y tendencia.
  var COLORS = { team: '#9d1009', similar: '#f4949d', others: '#8fb0cf', trend: 'rgba(80,80,80,0.7)' };

  // Etiquetas legibles de las métricas.
  var LABELS = {
    ExpectedGoalsPer90: 'xG /90', GoalsPer90: 'Goals /90', TotalShotsPer90: 'Shots /90', ShotsOnTargetPer90: 'Shots on target /90',
    BigChancesCreatedPer90: 'Big chances /90', BigChanceConversion: 'Big chance conversion', FinalThirdEntriesPer90: 'Final third entries /90',
    TouchesInOppBoxPer90: 'Touches in opp. box /90', KeyPassesPer90: 'Key passes /90', ExpectedAssistsPer90: 'xA /90',
    BallPossession: 'Ball possession %', ProgressiveFieldTilt: 'Progressive field tilt', PassAccuracy: 'Pass accuracy %',
    LongBallShare: 'Long ball share', CrossesPer90: 'Crosses /90', CrossAccuracy: 'Cross accuracy %', TacklesPer90: 'Tackles /90',
    InterceptionsPer90: 'Interceptions /90', DuelWinRate: 'Duel win %', AerialWinRate: 'Aerial win %', GoalsConcededPer90: 'Goals conceded /90'
  };

  // Presets de scatter (par de métricas X-Y).
  var PRESETS = [
    { label: 'xG vs Goals', x: 'ExpectedGoalsPer90', y: 'GoalsPer90' },
    { label: 'Shots vs Shots on target', x: 'TotalShotsPer90', y: 'ShotsOnTargetPer90' },
    { label: 'Big chances vs Conversion', x: 'BigChancesCreatedPer90', y: 'BigChanceConversion' },
    { label: 'Final third entries vs Box touches', x: 'FinalThirdEntriesPer90', y: 'TouchesInOppBoxPer90' },
    { label: 'Key passes vs xA', x: 'KeyPassesPer90', y: 'ExpectedAssistsPer90' },
    { label: 'Possession vs Field tilt', x: 'BallPossession', y: 'ProgressiveFieldTilt' },
    { label: 'Pass accuracy vs Long ball share', x: 'PassAccuracy', y: 'LongBallShare' },
    { label: 'Crosses vs Cross accuracy', x: 'CrossesPer90', y: 'CrossAccuracy' },
    { label: 'Tackles vs Interceptions', x: 'TacklesPer90', y: 'InterceptionsPer90' },
    { label: 'Duel win % vs Aerial win %', x: 'DuelWinRate', y: 'AerialWinRate' },
    { label: 'Goals vs Goals conceded', x: 'GoalsPer90', y: 'GoalsConcededPer90' },
    { label: 'xG vs Goals conceded', x: 'ExpectedGoalsPer90', y: 'GoalsConcededPer90' }
  ];

  // Opciones por defecto.
  var DEFAULTS = {
    maxLabels: 8, teamSize: 16, otherSize: 9, simSize: 12,
    markerBorder: 'rgba(0,0,0,0.45)', axisColor: '#666', splitColor: 'rgba(0,0,0,0.08)'
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[team_metrics_scatter] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Etiqueta legible de una métrica.
  function labelOf(m) { return LABELS[m] || m.replace(/Per90/, ' /90').replace(/([a-z])([A-Z])/g, '$1 $2'); }

  // Recta de regresión por mínimos cuadrados sobre los puntos.
  function linReg(pts) {
    var n = pts.length;
    if (n < 2) return null;
    var sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (var i = 0; i < n; i++) { var p = pts[i]; sx += p.x; sy += p.y; sxx += p.x * p.x; sxy += p.x * p.y; }
    var den = n * sxx - sx * sx;
    if (den === 0) return null;
    var b = (n * sxy - sx * sy) / den;
    return { a: (sy - b * sx) / n, b: b };
  }

  // IDs de los equipos más destacados (mayor suma normalizada x+y).
  function standoutIds(pts, maxN) {
    var xs = pts.map(function (p) { return p.x; }), ys = pts.map(function (p) { return p.y; });
    var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs);
    var miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
    var rx = maxx - minx || 1, ry = maxy - miny || 1;
    var scored = pts.map(function (p) { return { id: p.id, s: (p.x - minx) / rx + (p.y - miny) / ry }; });
    scored.sort(function (a, b) { return b.s - a.s; });
    var set = {};
    scored.slice(0, maxN).forEach(function (o) { set[o.id] = true; });
    return set;
  }

  // Crea el DOM (desplegable + checkbox + contenedor del scatter).
  function buildDom(el) {
    el.innerHTML = '';
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;align-items:center;gap:8px;margin:0 0 8px;font:13px system-ui,sans-serif;color:#222;';
    var label = document.createElement('span'); label.textContent = 'Chart:';
    var select = document.createElement('select');
    select.style.cssText = 'padding:5px 8px;border:1px solid #ccc;border-radius:4px;font:13px system-ui,sans-serif;';
    PRESETS.forEach(function (p, i) { var o = document.createElement('option'); o.value = String(i); o.textContent = p.label; select.appendChild(o); });
    // Selector para pintar a los equipos similares.
    var simLabel = document.createElement('label');
    simLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;margin-left:8px;';
    var simCb = document.createElement('input'); simCb.type = 'checkbox';
    simLabel.appendChild(simCb); simLabel.appendChild(document.createTextNode('Paint similar teams'));
    controls.appendChild(label); controls.appendChild(select); controls.appendChild(simLabel);
    el.appendChild(controls);
    var chartDom = document.createElement('div');
    chartDom.style.cssText = 'width:100%;height:520px;';
    el.appendChild(chartDom);
    return { select: select, simCb: simCb, chartDom: chartDom };
  }

  /**
   * Dibuja el scatter de stats de equipo.
   * @param {Object} team Objeto del equipo (team.json) con .ID y .SimilarTeams
   * @param {Object} comparison team_stats_comparison.json
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {Object} { chart } o null si no hay datos
   */
  function renderTeamScatter(team, comparison, el, opts) {
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});
    var metrics = (comparison && comparison.Metrics) || {};
    if (!team || !metrics[team.ID]) { el.innerHTML = '<div style="font:14px system-ui;color:#a00;">No comparison data for this team.</div>'; return null; }

    // Conjunto de IDs de equipos similares.
    var similarIds = {};
    (team.SimilarTeams || []).forEach(function (s) { if (s && s.Team) similarIds[s.Team] = true; });
    var paintSimilar = false;

    var dom = buildDom(el);
    var chart = ec.getInstanceByDom(dom.chartDom) || ec.init(dom.chartDom);

    // Construye y dibuja el scatter para un preset (par de métricas).
    function render(preset) {
      // Puntos válidos (con ambas métricas).
      var pts = [];
      Object.keys(metrics).forEach(function (id) {
        var r = metrics[id];
        if (!r || !isNum(r[preset.x]) || !isNum(r[preset.y])) return;
        pts.push({ id: id, name: r.Name || id, x: r[preset.x], y: r[preset.y], main: id === team.ID });
      });
      if (!pts.length) { chart.clear(); return; }

      // Destacados a etiquetar (+ siempre el equipo de interés).
      var stand = standoutIds(pts, cfg.maxLabels);

      // Datos de la serie scatter.
      var data = pts.map(function (p) {
        var showLabel = p.main || stand[p.id];
        var isSim = !p.main && paintSimilar && similarIds[p.id];
        return {
          value: [p.x, p.y], name: p.name, main: p.main,
          symbolSize: p.main ? cfg.teamSize : (isSim ? cfg.simSize : cfg.otherSize),
          itemStyle: {
            color: p.main ? COLORS.team : (isSim ? COLORS.similar : COLORS.others),
            borderColor: p.main ? '#fff' : (isSim ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.2)'),
            borderWidth: p.main ? 2 : (isSim ? 1 : 0.5),
            opacity: p.main ? 1 : (isSim ? 1 : 0.85)
          },
          label: showLabel ? {
            show: true, position: 'top', formatter: p.name,
            color: p.main ? COLORS.team : '#333', fontSize: p.main ? 12 : 11, fontWeight: p.main ? 'bold' : 'normal'
          } : { show: false },
          z: p.main ? 10 : (isSim ? 5 : 1)
        };
      });

      // Recta de tendencia.
      var reg = linReg(pts);
      var trendData = [];
      if (reg) {
        var xs = pts.map(function (p) { return p.x; });
        var xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
        trendData = [[xmin, reg.a + reg.b * xmin], [xmax, reg.a + reg.b * xmax]];
      }

      chart.setOption({
        backgroundColor: 'transparent', animation: false,
        grid: { left: 70, right: 28, top: 24, bottom: 56 },
        tooltip: {
          trigger: 'item', confine: true,
          formatter: function (p) {
            if (p.seriesId === 'trend') return '';
            return '<b>' + p.data.name + '</b><br/>' + labelOf(preset.x) + ': ' + p.value[0] + '<br/>' + labelOf(preset.y) + ': ' + p.value[1];
          }
        },
        xAxis: { type: 'value', scale: true, name: labelOf(preset.x), nameLocation: 'middle', nameGap: 30, nameTextStyle: { color: '#333', fontSize: 12 }, axisLine: { lineStyle: { color: cfg.axisColor } }, axisLabel: { color: cfg.axisColor }, splitLine: { lineStyle: { color: cfg.splitColor } } },
        yAxis: { type: 'value', scale: true, name: labelOf(preset.y), nameLocation: 'middle', nameGap: 50, nameTextStyle: { color: '#333', fontSize: 12 }, axisLine: { lineStyle: { color: cfg.axisColor } }, axisLabel: { color: cfg.axisColor }, splitLine: { lineStyle: { color: cfg.splitColor } } },
        series: [
          { id: 'trend', type: 'line', data: trendData, showSymbol: false, silent: true, z: 0, lineStyle: { color: COLORS.trend, width: 1.5, type: 'dashed' } },
          { id: 'teams', type: 'scatter', data: data, z: 2, labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' } }
        ]
      }, true);
    }

    // Render inicial y controles.
    var currentPreset = PRESETS[0];
    render(currentPreset);
    dom.select.addEventListener('change', function () { currentPreset = PRESETS[+dom.select.value] || PRESETS[0]; render(currentPreset); });
    dom.simCb.addEventListener('change', function () { paintSimilar = dom.simCb.checked; render(currentPreset); });

    // Reajuste al redimensionar.
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(function () { chart.resize(); }); ro.observe(el);
    } else if (typeof global.addEventListener === 'function') {
      global.addEventListener('resize', function () { chart.resize(); });
    }

    return { chart: chart };
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderTeamScatter = renderTeamScatter;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderTeamScatter;
  }
})(typeof window !== 'undefined' ? window : this);
