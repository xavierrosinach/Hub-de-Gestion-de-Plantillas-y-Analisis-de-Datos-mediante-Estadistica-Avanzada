/**
 * CREACIÓN DE UN GRÁFICO DE DIFERENCIA DE GOLES POR PARTIDO (EQUIPO) CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Fondo gris semitransparente común a las tarjetas.
  var UI_BG = 'rgba(60,60,60,0.6)';

  // Opciones por defecto (sobreescribibles con el argumento opts).
  var DEFAULTS = {
    crestBase:    'https://pub-f177abd2266143fa9dc17043d96d50da.r2.dev/images/team/',
    crest:        'opponent',                            // 'opponent' | 'own'
    crestSize:    28,
    dotSize:      9,
    visibleMatches: 10,
    diffMin:      -3,                                    // diferencia del color rojo
    diffMax:      3,                                     // diferencia del color verde
    colorRange:   ['#d32f2f', '#e9c46a', '#2e9e4f'],     // rojo -> neutro -> verde
    lineWidth:    3,
    axisColor:    '#666',
    splitColor:   'rgba(0,0,0,0.08)',
    zeroColor:    'rgba(0,0,0,0.35)',
    cardText:     'Mean goal diff: ',
    showCard:     true,
    pad:          12
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[team_goaldiff_chart] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Convierte una fecha "dd/mm/yyyy" en objeto Date (para ordenar).
  function parseDate(d) {
    var p = (d || '').split('/');
    return p.length === 3 ? new Date(+p[2], +p[1] - 1, +p[0]) : new Date(0);
  }

  // Extrae los partidos (soporta Matches como lista, diccionario u objeto único) y los ordena.
  function extractMatches(team) {
    var raw = (team && team.Matches) || [];
    var arr = [];
    // Añade un partido si tiene Info y diferencia de goles.
    function add(m) {
      if (!m || !m.Info) return;
      var info = m.Info, opp = m.Opponent || {};
      // Diferencia de goles: usa ScoreDifference o, si falta, Score - Opponent.Score.
      var diff = isNum(info.ScoreDifference) ? info.ScoreDifference
                 : (isNum(info.Score) && isNum(opp.Score) ? info.Score - opp.Score : null);
      if (diff == null) return;
      arr.push({
        diff: diff,
        date: info.Date || '-',
        league: info.League || '-',
        homeAway: info.HomeAway || '-',
        teamScore: isNum(info.Score) ? info.Score : null,
        oppScore: isNum(opp.Score) ? opp.Score : null,
        oppName: opp.Name || '-',
        oppId: opp.Opponent || opp.ID || null,
        _t: parseDate(info.Date)
      });
    }
    if (Array.isArray(raw)) raw.forEach(add);                 // lista de partidos
    else if (raw.Info) add(raw);                              // un único partido
    else Object.keys(raw).forEach(function (k) { add(raw[k]); }); // diccionario por id
    arr.sort(function (a, b) { return a._t - b._t; });
    return arr;
  }

  // Resultado (W/D/L) y marcador en orden local-visitante para el tooltip.
  function resultText(m) {
    if (m.teamScore == null || m.oppScore == null) return '-';
    var res = m.teamScore > m.oppScore ? 'Win' : (m.teamScore < m.oppScore ? 'Loss' : 'Draw');
    var home = m.homeAway === 'Home';
    var hs = home ? m.teamScore : m.oppScore;
    var as = home ? m.oppScore : m.teamScore;
    return res + ' (' + hs + ' - ' + as + ')';
  }

  // Media de la diferencia de goles.
  function meanDiff(matches) {
    if (!matches.length) return 0;
    var s = 0;
    matches.forEach(function (m) { s += m.diff; });
    return s / matches.length;
  }

  // Tarjeta (graphic) con la media arriba a la derecha, con fondo gris.
  function meanCard(cfg, mean) {
    var text = cfg.cardText + (mean >= 0 ? '+' : '') + mean.toFixed(2);
    var w = text.length * 7 + 18, h = 24;
    return {
      type: 'group', right: 12, top: 10, z: 50, silent: true,
      children: [
        { type: 'rect', shape: { x: 0, y: 0, width: w, height: h, r: 4 }, style: { fill: UI_BG } },
        { type: 'text', x: 9, y: h / 2, style: { text: text, fill: '#fff', font: '13px system-ui, sans-serif', textVerticalAlign: 'middle' } }
      ]
    };
  }

  /**
   * Dibuja el gráfico de diferencia de goles por partido.
   * @param {Object} team Objeto del equipo (team.json) con .Matches
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {ECharts}
   */
  function renderTeamGoalDiffChart(team, el, opts) {
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});

    var chart = ec.getInstanceByDom(el) || ec.init(el);
    var matches = extractMatches(team);
    var n = matches.length;

    // Etiquetas del eje X (fecha dd/mm).
    var labels = matches.map(function (m) { return m.date.slice(0, 5); });

    // Puntos: valor = diferencia de goles, marcador = escudo (offset arriba/abajo según signo).
    var points = matches.map(function (m) {
      var crestId = cfg.crest === 'own' ? (team && team.ID) : m.oppId;
      var off = m.diff >= 0 ? -cfg.crestSize * 0.9 : cfg.crestSize * 0.9;
      return {
        value: m.diff,
        match: m,
        symbol: crestId ? 'image://' + cfg.crestBase + crestId + '.png' : 'circle',
        symbolSize: cfg.crestSize,
        symbolOffset: [0, off]
      };
    });

    // Rango del eje Y simétrico, con margen para el escudo.
    var maxAbs = 3;
    matches.forEach(function (m) { if (Math.abs(m.diff) > maxAbs) maxAbs = Math.abs(m.diff); });
    maxAbs = Math.ceil(maxAbs) + 1;

    // Ventana inicial: últimos N partidos.
    var startIndex = Math.max(0, n - cfg.visibleMatches);
    var endIndex = Math.max(0, n - 1);

    var mean = meanDiff(matches);

    // Color de un punto según su diferencia de goles (misma escala que la línea).
    function hx(c){ c=String(c).replace('#',''); return [parseInt(c.slice(0,2),16),parseInt(c.slice(2,4),16),parseInt(c.slice(4,6),16)]; }
    function colorScale(diff){
      var cr=cfg.colorRange, t=(diff-cfg.diffMin)/(cfg.diffMax-cfg.diffMin); t=Math.max(0,Math.min(1,t));
      var seg=t*(cr.length-1), i=Math.floor(seg), f=seg-i; if(i>=cr.length-1){ i=cr.length-2; f=1; }
      var a=hx(cr[i]), b=hx(cr[i+1]);
      return 'rgb('+Math.round(a[0]+(b[0]-a[0])*f)+','+Math.round(a[1]+(b[1]-a[1])*f)+','+Math.round(a[2]+(b[2]-a[2])*f)+')';
    }
    // Puntos de color en el valor (además del escudo).
    var dotData = matches.map(function (m) { return { value: m.diff, itemStyle: { color: colorScale(m.diff) } }; });

    var option = {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 44, right: 18, top: 24, bottom: 64 },
      // Escala de color de la diferencia de goles (degrada la línea).
      visualMap: {
        show: false, type: 'continuous', seriesIndex: 0,
        min: cfg.diffMin, max: cfg.diffMax, inRange: { color: cfg.colorRange }
      },
      tooltip: {
        trigger: 'axis', confine: true,
        formatter: function (ps) {
          var m = ps && ps[0] && ps[0].data && ps[0].data.match;
          if (!m) return '';
          return '<b>' + m.oppName + '</b>' +
            '<br/>Goal diff: ' + (m.diff >= 0 ? '+' : '') + m.diff +
            '<br/>Tournament: ' + m.league +
            '<br/>Date: ' + m.date +
            '<br/>Home/Away: ' + m.homeAway +
            '<br/>Result: ' + resultText(m);
        }
      },
      xAxis: {
        type: 'category', data: labels, boundaryGap: true,
        axisLine: { lineStyle: { color: cfg.axisColor } },
        axisTick: { alignWithLabel: true },
        axisLabel: { color: cfg.axisColor, fontSize: 11 }
      },
      yAxis: {
        type: 'value', min: -maxAbs, max: maxAbs,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: cfg.axisColor, fontSize: 11 },
        splitLine: { lineStyle: { color: cfg.splitColor } }
      },
      dataZoom: [
        { type: 'inside', startValue: startIndex, endValue: endIndex, minValueSpan: 2 },
        { type: 'slider', startValue: startIndex, endValue: endIndex, bottom: 16, height: 18 }
      ],
      graphic: cfg.showCard ? [meanCard(cfg, mean)] : [],
      series: [{
        id: 'gd', name: 'Goal diff', type: 'line', data: points,
        showSymbol: true, lineStyle: { width: cfg.lineWidth }, z: 5,
        // Línea de base en 0 (separa por encima/por debajo).
        markLine: { silent: true, symbol: 'none', label: { show: false },
          lineStyle: { type: 'dashed', color: cfg.zeroColor, width: 1.5 }, data: [{ yAxis: 0 }] }
      },{
        // Punto de color en el valor real de cada partido.
        id: 'gddots', type: 'scatter', data: dotData, symbol: 'circle', symbolSize: cfg.dotSize,
        itemStyle: { borderColor: '#fff', borderWidth: 1.5 }, z: 6, silent: true
      }]
    };

    chart.setOption(option, true);

    // Reajuste al redimensionar.
    if (!chart.__gdResizeBound) {
      var onResize = function () { chart.resize(); };
      if (typeof ResizeObserver !== 'undefined') { var ro = new ResizeObserver(onResize); ro.observe(el); chart.__gdResizeObserver = ro; }
      else if (typeof global.addEventListener === 'function') { global.addEventListener('resize', onResize); }
      chart.__gdResizeBound = true;
    }

    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderTeamGoalDiffChart = renderTeamGoalDiffChart;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderTeamGoalDiffChart;
  }
})(typeof window !== 'undefined' ? window : this);
