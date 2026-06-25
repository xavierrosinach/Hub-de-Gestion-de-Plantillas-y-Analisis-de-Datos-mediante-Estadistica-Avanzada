/**
 * CREACIÓN DE UN GRÁFICO DE RATING POR PARTIDO CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Fondo gris semitransparente común a las tarjetas/controles.
  var UI_BG = 'rgba(60,60,60,0.6)';

  // Opciones por defecto (sobreescribibles con el argumento opts).
  var DEFAULTS = {
    visibleMatches: 10,
    ratingMin:      5,                                   // rating del color rojo
    ratingMax:      10,                                  // rating del color verde
    colorRange:     ['#d32f2f', '#f4d03f', '#2e9e4f'],   // rojo -> amarillo -> verde
    lineWidth:      3,
    symbolSize:     9,
    symbolBorder:   'rgba(0,0,0,0.25)',
    axisColor:      '#666',
    splitColor:     'rgba(0,0,0,0.08)',
    cardText:       'Mean rating: ',
    showCard:       true,
    pad:            12
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[player_rating_chart] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Convierte una fecha "dd/mm/yyyy" en objeto Date (para ordenar).
  function parseDate(d) {
    var p = (d || '').split('/');
    return p.length === 3 ? new Date(+p[2], +p[1] - 1, +p[0]) : new Date(0);
  }

  // Extrae y ordena los partidos cronológicamente con los campos del tooltip.
  function extractMatches(data) {
    var raw = (data && data.Matches) || {};
    var list = [];
    Object.keys(raw).forEach(function (k) {
      var m = raw[k] || {};
      var info = m.Info || {};
      var opp = m.Opponent || {};
      if (!isNum(info.Rating)) return;
      list.push({
        rating: info.Rating,
        tournament: info.League || '-',
        date: info.Date || '-',
        opponent: opp.Name || '-',
        homeAway: info.HomeAway || '-',
        teamScore: isNum(info.Score) ? info.Score : null,
        oppScore: isNum(opp.Score) ? opp.Score : null,
        minutes: isNum(info.MinutesPlayed) ? info.MinutesPlayed : null,
        _t: parseDate(info.Date)
      });
    });
    list.sort(function (a, b) { return a._t - b._t; });
    return list;
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

  // Media de rating de todos los partidos.
  function meanRating(matches) {
    if (!matches.length) return 0;
    var s = 0;
    matches.forEach(function (m) { s += m.rating; });
    return s / matches.length;
  }

  // Tarjeta (graphic) con el "Mean rating:" arriba a la derecha, con fondo gris.
  function meanCard(cfg, mean) {
    var text = cfg.cardText + mean.toFixed(2);
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
   * Dibuja el gráfico de rating por partido.
   * @param {Object} data Objeto del jugador (player.json) con .Matches
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {ECharts}
   */
  function renderPlayerRatingChart(data, el, opts) {
    // Instancia de ECharts y configuración combinada.
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});

    // Instancia (reutilizada si ya existía) y partidos ordenados.
    var chart = ec.getInstanceByDom(el) || ec.init(el);
    var matches = extractMatches(data);
    var n = matches.length;

    // Etiquetas del eje X (fecha) y puntos (rating + datos del tooltip).
    var labels = matches.map(function (m) { return m.date.slice(0, 5); });   // dd/mm
    var points = matches.map(function (m) { return { value: m.rating, match: m }; });

    // Rango del eje Y ajustado a los datos.
    var ratings = matches.map(function (m) { return m.rating; });
    var yMin = Math.max(0, Math.floor(Math.min.apply(null, ratings.concat(10)) - 0.5));
    var yMax = Math.min(10, Math.ceil(Math.max.apply(null, ratings.concat(0)) + 0.5));

    // Ventana inicial: últimos N partidos.
    var startIndex = Math.max(0, n - cfg.visibleMatches);
    var endIndex = Math.max(0, n - 1);

    // Tarjeta de media.
    var mean = meanRating(matches);

    // Configuración completa del gráfico.
    var option = {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 44, right: 18, top: 24, bottom: 64 },
      // Escala de color del rating (no visible): tiñe puntos y degrada la línea.
      visualMap: {
        show: false, type: 'continuous', seriesIndex: 0,
        min: cfg.ratingMin, max: cfg.ratingMax,
        inRange: { color: cfg.colorRange }
      },
      // Tooltip con los datos del partido (rival, torneo, fecha, resultado, minutos).
      tooltip: {
        trigger: 'axis', confine: true,
        formatter: function (ps) {
          var m = ps && ps[0] && ps[0].data && ps[0].data.match;
          if (!m) return '';
          return '<b>' + m.opponent + '</b>' +
            '<br/>Rating: ' + m.rating.toFixed(2) +
            '<br/>Tournament: ' + m.tournament +
            '<br/>Date: ' + m.date +
            '<br/>Opponent: ' + m.opponent +
            '<br/>Home/Away: ' + m.homeAway +
            '<br/>Result: ' + resultText(m) +
            '<br/>Minutes: ' + (m.minutes == null ? '-' : Math.round(m.minutes));
        }
      },
      // Eje X: fecha (dd/mm) de cada partido.
      xAxis: {
        type: 'category', data: labels, boundaryGap: true,
        axisLine: { lineStyle: { color: cfg.axisColor } },
        axisTick: { alignWithLabel: true },
        axisLabel: { color: cfg.axisColor, fontSize: 11 }
      },
      // Eje Y: rating, acotado al rango de los datos.
      yAxis: {
        type: 'value', min: yMin, max: yMax,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { color: cfg.axisColor, fontSize: 11 },
        splitLine: { lineStyle: { color: cfg.splitColor } }
      },
      // Scrollbar inferior + arrastre interior para navegar hacia atrás.
      dataZoom: [
        { type: 'inside', startValue: startIndex, endValue: endIndex, minValueSpan: 2 },
        { type: 'slider', startValue: startIndex, endValue: endIndex, bottom: 16, height: 18 }
      ],
      // Tarjeta con la media de rating (arriba a la derecha).
      graphic: cfg.showCard ? [meanCard(cfg, mean)] : [],
      // Serie de línea: un punto por partido, coloreado por el visualMap del rating.
      series: [{
        id: 'rating', name: 'Rating', type: 'line',
        data: points, showSymbol: true, symbol: 'circle', symbolSize: cfg.symbolSize,
        itemStyle: { borderColor: cfg.symbolBorder, borderWidth: 1 },
        lineStyle: { width: cfg.lineWidth },
        z: 5
      }]
    };

    chart.setOption(option, true);

    // Reajuste al redimensionar el contenedor.
    if (!chart.__ratingResizeBound) {
      var onResize = function () { chart.resize(); };
      if (typeof ResizeObserver !== 'undefined') { var ro = new ResizeObserver(onResize); ro.observe(el); chart.__ratingResizeObserver = ro; }
      else if (typeof global.addEventListener === 'function') { global.addEventListener('resize', onResize); }
      chart.__ratingResizeBound = true;
    }

    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderPlayerRatingChart = renderPlayerRatingChart;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerRatingChart;
  }
})(typeof window !== 'undefined' ? window : this);
