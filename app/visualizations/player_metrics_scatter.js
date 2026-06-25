/**
 * CREACIÓN DE UN SCATTER DE MÉTRICAS POR POSICIÓN CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Colores del jugador relevante, similares, resto y tendencia.
  var COLORS = { player: '#9d1009', similar: '#f4949d', others: '#8fb0cf', trend: 'rgba(80,80,80,0.7)' };

  // Etiquetas legibles de las métricas (totales).
  var LABELS = {
    Goals: 'Goals', ExpectedGoals: 'xG', TotalShots: 'Shots', ShotsOnTarget: 'Shots on target',
    GoalAssists: 'Assists', ExpectedAssists: 'xA', KeyPasses: 'Key passes', BigChancesCreated: 'Big chances created',
    Contests: 'Dribbles', ContestsWon: 'Dribbles won', Crosses: 'Crosses', AccurateCrosses: 'Accurate crosses',
    Tackles: 'Tackles', TacklesWon: 'Tackles won', Interceptions: 'Interceptions', DuelsWon: 'Duels won',
    AerialWon: 'Aerials won', BallRecoveries: 'Ball recoveries', Clearances: 'Clearances', OutfielderBlocks: 'Blocks',
    Passes: 'Passes', AccuratePasses: 'Accurate passes', Saves: 'Saves', GoalsConceded: 'Goals conceded',
    CleanSheets: 'Clean sheets', Touches: 'Touches', WasFouled: 'Times fouled'
  };

  // Presets de scatter (par de métricas X-Y) por posición.
  var ATT = [
    { label: 'Goals vs xG', x: 'ExpectedGoals', y: 'Goals' },
    { label: 'Shots vs Goals', x: 'TotalShots', y: 'Goals' },
    { label: 'Assists vs xA', x: 'ExpectedAssists', y: 'GoalAssists' },
    { label: 'Key passes vs Big chances created', x: 'KeyPasses', y: 'BigChancesCreated' },
    { label: 'Dribbles attempted vs won', x: 'Contests', y: 'ContestsWon' }
  ];
  var WING = [
    { label: 'Goals vs xG', x: 'ExpectedGoals', y: 'Goals' },
    { label: 'Assists vs xA', x: 'ExpectedAssists', y: 'GoalAssists' },
    { label: 'Dribbles attempted vs won', x: 'Contests', y: 'ContestsWon' },
    { label: 'Crosses vs Accurate crosses', x: 'Crosses', y: 'AccurateCrosses' },
    { label: 'Key passes vs Big chances created', x: 'KeyPasses', y: 'BigChancesCreated' }
  ];
  var FB = [
    { label: 'Crosses vs Accurate crosses', x: 'Crosses', y: 'AccurateCrosses' },
    { label: 'Key passes vs Assists', x: 'KeyPasses', y: 'GoalAssists' },
    { label: 'Tackles vs Interceptions', x: 'Tackles', y: 'Interceptions' },
    { label: 'Dribbles attempted vs won', x: 'Contests', y: 'ContestsWon' }
  ];
  var PRESETS = {
    GK: [
      { label: 'Saves vs Goals conceded', x: 'GoalsConceded', y: 'Saves' },
      { label: 'Clean sheets vs Goals conceded', x: 'GoalsConceded', y: 'CleanSheets' },
      { label: 'Passing volume vs accuracy', x: 'Passes', y: 'AccuratePasses' }
    ],
    CB: [
      { label: 'Tackles vs Interceptions', x: 'Tackles', y: 'Interceptions' },
      { label: 'Duels won vs Aerials won', x: 'DuelsWon', y: 'AerialWon' },
      { label: 'Recoveries vs Clearances', x: 'BallRecoveries', y: 'Clearances' },
      { label: 'Passing volume vs accuracy', x: 'Passes', y: 'AccuratePasses' }
    ],
    LB: FB, RB: FB,
    DM: [
      { label: 'Tackles vs Interceptions', x: 'Tackles', y: 'Interceptions' },
      { label: 'Recoveries vs Duels won', x: 'BallRecoveries', y: 'DuelsWon' },
      { label: 'Passing volume vs accuracy', x: 'Passes', y: 'AccuratePasses' },
      { label: 'Key passes vs xA', x: 'KeyPasses', y: 'ExpectedAssists' }
    ],
    AM: ATT, LW: WING, RW: WING, ST: [
      { label: 'Goals vs xG', x: 'ExpectedGoals', y: 'Goals' },
      { label: 'Shots vs Goals', x: 'TotalShots', y: 'Goals' },
      { label: 'Shots on target vs Goals', x: 'ShotsOnTarget', y: 'Goals' },
      { label: 'Assists vs xA', x: 'ExpectedAssists', y: 'GoalAssists' },
      { label: 'Aerials won vs Duels won', x: 'AerialWon', y: 'DuelsWon' }
    ]
  };

  // Opciones por defecto.
  var DEFAULTS = {
    minMinutes:   500,   // minutos mínimos para incluir un jugador
    maxLabels:    8,     // nº de jugadores destacados etiquetados
    playerSize:   15,
    otherSize:    8,
    axisColor:    '#666',
    splitColor:   'rgba(0,0,0,0.08)'
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[player_metrics_scatter] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Etiqueta legible de una métrica.
  function labelOf(m) { return LABELS[m] || m.replace(/([a-z])([A-Z])/g, '$1 $2'); }

  // Localiza la posición del jugador dentro de la estructura de comparación.
  function findPosition(player, comparison) {
    var id = player && player.ID;
    var prefs = [player && player.FirstPos, player && player.SecondPos];
    for (var i = 0; i < prefs.length; i++) {
      var p = prefs[i];
      if (p && comparison[p] && comparison[p].Metrics && comparison[p].Metrics[id]) return p;
    }
    var keys = Object.keys(comparison);
    for (var k = 0; k < keys.length; k++) {
      var mc = comparison[keys[k]].Metrics;
      if (mc && mc[id]) return keys[k];
    }
    return null;
  }

  // Recta de regresión por mínimos cuadrados sobre los puntos.
  function linReg(pts) {
    var n = pts.length;
    if (n < 2) return null;
    var sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (var i = 0; i < n; i++) { var p = pts[i]; sx += p.x; sy += p.y; sxx += p.x * p.x; sxy += p.x * p.y; }
    var den = n * sxx - sx * sx;
    if (den === 0) return null;
    var b = (n * sxy - sx * sy) / den;
    var a = (sy - b * sx) / n;
    return { a: a, b: b };
  }

  // Índices de los jugadores más destacados (mayor suma normalizada x+y).
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

  // Crea el DOM (desplegable + contenedor del scatter).
  function buildDom(el, presets) {
    el.innerHTML = '';
    // Barra de controles
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;align-items:center;gap:8px;margin:0 0 8px;font:13px system-ui,sans-serif;color:#222;';
    var label = document.createElement('span');
    label.textContent = 'Chart:';
    var select = document.createElement('select');
    select.style.cssText = 'padding:5px 8px;border:1px solid #ccc;border-radius:4px;font:13px system-ui,sans-serif;';
    presets.forEach(function (p, i) { var o = document.createElement('option'); o.value = String(i); o.textContent = p.label; select.appendChild(o); });
    controls.appendChild(label);
    controls.appendChild(select);
    // Selector para pintar a los jugadores similares
    var simLabel = document.createElement('label');
    simLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;margin-left:8px;';
    var simCb = document.createElement('input');
    simCb.type = 'checkbox';
    simLabel.appendChild(simCb);
    simLabel.appendChild(document.createTextNode('Paint similar players'));
    controls.appendChild(simLabel);
    el.appendChild(controls);
    // Contenedor del gráfico
    var chartDom = document.createElement('div');
    chartDom.style.cssText = 'width:100%;height:520px;';
    el.appendChild(chartDom);
    return { select: select, simCb: simCb, chartDom: chartDom };
  }

  /**
   * Dibuja el scatter de métricas del jugador por posición.
   * @param {Object} player Objeto del jugador (player.json)
   * @param {Object} comparison player_stats_comparison.json
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {Object} { chart } o null si no hay datos
   */
  function renderPlayerMetricsScatter(player, comparison, el, opts) {
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});
    comparison = comparison || {};

    // Posición del jugador y métricas de esa posición.
    var pos = findPosition(player, comparison);
    if (!pos) { el.innerHTML = '<div style="font:14px system-ui;color:#a00;">No comparison data for this player.</div>'; return null; }
    var metrics = comparison[pos].Metrics;
    var presets = PRESETS[pos] || PRESETS.AM;

    // Conjunto de IDs de jugadores similares (para pintarlos resaltados).
    var similarIds = {};
    (player.SimilarPlayers || []).forEach(function (s) { if (s && s.Player) similarIds[s.Player] = true; });

    // Estado del selector "Paint similar players".
    var paintSimilar = false;

    // DOM e instancia del gráfico.
    var dom = buildDom(el, presets);
    var chart = ec.getInstanceByDom(dom.chartDom) || ec.init(dom.chartDom);

    // Construye y dibuja el scatter para un preset (par de métricas).
    function render(preset) {
      // Puntos válidos (con ambas métricas) filtrando por minutos; el jugador relevante siempre entra.
      var pts = [];
      Object.keys(metrics).forEach(function (id) {
        var r = metrics[id];
        if (!r || !isNum(r[preset.x]) || !isNum(r[preset.y])) return;
        var enough = !isNum(r.MinutesPlayed) || r.MinutesPlayed >= cfg.minMinutes;
        if (!enough && id !== player.ID) return;
        pts.push({ id: id, name: r.Name || id, x: r[preset.x], y: r[preset.y], main: id === player.ID });
      });
      if (!pts.length) { chart.clear(); return; }

      // Destacados a etiquetar (+ siempre el jugador relevante).
      var stand = standoutIds(pts, cfg.maxLabels);

      // Datos de la serie scatter con etiqueta solo en destacados/relevante.
      var data = pts.map(function (p) {
        var showLabel = p.main || stand[p.id];
        // ¿Pintar como similar? (solo color, sin nombre)
        var isSim = !p.main && paintSimilar && similarIds[p.id];
        return {
          value: [p.x, p.y], name: p.name, main: p.main,
          symbolSize: p.main ? cfg.playerSize : (isSim ? cfg.otherSize + 4 : cfg.otherSize),
          itemStyle: {
            color: p.main ? COLORS.player : (isSim ? COLORS.similar : COLORS.others),
            borderColor: p.main ? '#fff' : (isSim ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.2)'),
            borderWidth: p.main ? 2 : (isSim ? 1 : 0.5),
            opacity: p.main ? 1 : (isSim ? 1 : 0.85)
          },
          label: showLabel ? {
            show: true, position: 'top', formatter: p.name,
            color: p.main ? COLORS.player : '#333', fontSize: p.main ? 12 : 11,
            fontWeight: p.main ? 'bold' : 'normal'
          } : { show: false },
          z: p.main ? 10 : (isSim ? 5 : 1)
        };
      });

      // Recta de tendencia (media que siguen los jugadores).
      var reg = linReg(pts);
      var trendData = [];
      if (reg) {
        var xs = pts.map(function (p) { return p.x; });
        var xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
        trendData = [[xmin, reg.a + reg.b * xmin], [xmax, reg.a + reg.b * xmax]];
      }

      chart.setOption({
        backgroundColor: 'transparent',
        animation: false,
        grid: { left: 64, right: 28, top: 24, bottom: 56 },
        tooltip: {
          trigger: 'item', confine: true,
          formatter: function (p) {
            if (p.seriesId === 'trend') return '';
            return '<b>' + p.data.name + '</b><br/>' + labelOf(preset.x) + ': ' + p.value[0] +
              '<br/>' + labelOf(preset.y) + ': ' + p.value[1];
          }
        },
        xAxis: {
          type: 'value', scale: true, name: labelOf(preset.x), nameLocation: 'middle', nameGap: 30,
          nameTextStyle: { color: '#333', fontSize: 12 },
          axisLine: { lineStyle: { color: cfg.axisColor } }, axisLabel: { color: cfg.axisColor },
          splitLine: { lineStyle: { color: cfg.splitColor } }
        },
        yAxis: {
          type: 'value', scale: true, name: labelOf(preset.y), nameLocation: 'middle', nameGap: 44,
          nameTextStyle: { color: '#333', fontSize: 12 },
          axisLine: { lineStyle: { color: cfg.axisColor } }, axisLabel: { color: cfg.axisColor },
          splitLine: { lineStyle: { color: cfg.splitColor } }
        },
        series: [
          // Línea de tendencia discontinua gris (debajo de los puntos).
          { id: 'trend', type: 'line', data: trendData, showSymbol: false, silent: true, z: 0,
            lineStyle: { color: COLORS.trend, width: 1.5, type: 'dashed' } },
          // Puntos; labelLayout evita que las etiquetas tapen puntos.
          { id: 'players', type: 'scatter', data: data, z: 2,
            labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' } }
        ]
      }, true);
    }

    // Preset activo (para poder redibujar al cambiar el selector de similares).
    var currentPreset = presets[0];
    render(currentPreset);
    dom.select.addEventListener('change', function () { currentPreset = presets[+dom.select.value] || presets[0]; render(currentPreset); });
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
  global.renderPlayerMetricsScatter = renderPlayerMetricsScatter;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerMetricsScatter;
  }
})(typeof window !== 'undefined' ? window : this);
