/**
 * CREACIÓN DE UNA VISTA DE PORTERÍA (GOAL MOUTH) CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Fondo gris semitransparente de la leyenda.
  var UI_BG = 'rgba(60,60,60,0.6)';
  // Color por tipo: gol (dorado) y tiro parado (azul).
  var DEFAULT_COLORS = { 'Goal': '#ffd400', 'Saved Shot': '#36b3ff' };

  // Opciones por defecto
  var DEFAULTS = {
    colors:       DEFAULT_COLORS,
    shotSize:     11,
    goalSize:     17,
    markerBorder: 'rgba(0,0,0,0.55)',
    markerBorderWidth: 1,
    frameColor:   '#2b2b2b',
    frameWidth:   3,
    netColor:     'rgba(0,0,0,0.16)',
    netWidth:     1,
    goalAreaFill: 'rgba(0,0,0,0.04)',
    showLegend:   true,
    legendFontSize: 12,
    legendDotR:   6,
    showTooltip:  true,
    goalYmin:     45,
    goalYmax:     55,
    goalZmin:     0,
    goalZmax:     30,
    marginY:      2,
    marginZbottom: 2,
    marginZtop:   3,
    realGoalW:    7.32,
    realGoalH:    2.44,
    pad:          12
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[player_goal_map] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Color del tiro: dorado si es gol, azul (Saved Shot) en cualquier otro caso.
  function colorOf(type, colors) {
    return type === 'Goal' ? colors.Goal : colors['Saved Shot'];
  }

  // Filtra los tiros que acabaron a puerta (tienen GoalY y GoalZ).
  function onTargetShots(shots) {
    return shots.filter(function (s) { return s && isNum(s.GoalY) && isNum(s.GoalZ); });
  }

  // Calcula los márgenes del grid para centrar la portería con su proporción real.
  function computeGrid(el, pad, ratioHW) {
    // Dimensiones del contenedor.
    var W = el.clientWidth || el.offsetWidth || 760;
    var H = el.clientHeight || el.offsetHeight || 300;
    // Espacio disponible restando el padding.
    var availW = W - 2 * pad, availH = H - 2 * pad;
    // Ancho/alto del área de dibujo ajustada a la proporción.
    var w, h;
    if (availW * ratioHW <= availH) { w = availW; h = w * ratioHW; }
    else { h = availH; w = h / ratioHW; }
    // Offsets para centrar.
    var left = (W - w) / 2, top = (H - h) / 2;
    return { left: left, right: W - left - w, top: top, bottom: H - top - h };
  }

  // Custom renderItem que dibuja el marco de la portería, la red y el suelo.
  function frameRenderItem(cfg, axis) {
    return function (params, api) {
      // P(goalY, goalZ) -> pixel.
      var P = function (y, z) { return api.coord([y, z]); };
      // Acumulador de formas.
      var children = [];
      // Postes/larguero/suelo.
      var ym0 = cfg.goalYmin, ym1 = cfg.goalYmax, zm0 = cfg.goalZmin, zm1 = cfg.goalZmax;

      // Línea entre dos puntos (en coords de portería).
      function line(y1, z1, y2, z2, color, width) {
        var a = P(y1, z1), b = P(y2, z2);
        return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: { stroke: color, lineWidth: width, fill: 'none' }, silent: true };
      }

      // Relleno tenue del área de portería.
      var tl = P(ym0, zm1), br = P(ym1, zm0);
      children.push({ type: 'rect', shape: { x: Math.min(tl[0], br[0]), y: Math.min(tl[1], br[1]), width: Math.abs(br[0] - tl[0]), height: Math.abs(br[1] - tl[1]) }, style: { fill: cfg.goalAreaFill }, silent: true });

      // Red: líneas verticales internas.
      for (var y = ym0 + 1.5; y < ym1; y += 1.5) children.push(line(y, zm0, y, zm1, cfg.netColor, cfg.netWidth));
      // Red: líneas horizontales internas.
      for (var z = zm0 + 6; z < zm1; z += 6) children.push(line(ym0, z, ym1, z, cfg.netColor, cfg.netWidth));

      // Suelo (línea a ras a lo ancho del eje).
      children.push(line(axis.ymin, zm0, axis.ymax, zm0, cfg.frameColor, cfg.frameWidth * 0.6));
      // Postes y larguero.
      children.push(line(ym0, zm0, ym0, zm1, cfg.frameColor, cfg.frameWidth));
      children.push(line(ym1, zm0, ym1, zm1, cfg.frameColor, cfg.frameWidth));
      children.push(line(ym0, zm1, ym1, zm1, cfg.frameColor, cfg.frameWidth));

      return { type: 'group', children: children };
    };
  }

  // Construye los puntos del scatter (GoalY, GoalZ) con color y tamaño por tipo.
  function buildShotData(shots, cfg) {
    var pts = [];
    shots.forEach(function (s) {
      // Los goles se dibujan más grandes.
      var isGoal = s.Type === 'Goal';
      pts.push({
        value: [s.GoalY, s.GoalZ],
        name: s.Type,
        symbolSize: isGoal ? cfg.goalSize : cfg.shotSize,
        itemStyle: { color: colorOf(s.Type, cfg.colors), borderColor: cfg.markerBorder, borderWidth: cfg.markerBorderWidth },
        _shot: s
      });
    });
    return pts;
  }

  // Etiquetas presentes para la leyenda (Goal y/o Saved Shot).
  function presentLabels(shots) {
    var hasGoal = shots.some(function (s) { return s.Type === 'Goal'; });
    var hasOther = shots.some(function (s) { return s.Type !== 'Goal'; });
    var out = [];
    if (hasGoal) out.push('Goal');
    if (hasOther) out.push('Saved Shot');
    return out;
  }

  // Custom renderItem de la leyenda: caja gris + punto de color y nombre, abajo.
  function legendRenderItem(cfg, labels, axis) {
    return function (params, api) {
      if (!cfg.showLegend || !labels.length) return;
      // Métricas de maquetación.
      var fs = cfg.legendFontSize, r = cfg.legendDotR, gap = 18, charW = fs * 0.6;
      // Ancho estimado de cada entrada.
      var entries = labels.map(function (t) { return { t: t, w: 2 * r + 5 + t.length * charW }; });
      // Ancho total de la fila.
      var total = entries.reduce(function (a, e) { return a + e.w; }, 0) + gap * (entries.length - 1);
      // Anclaje: centro-inferior del área, en píxel.
      var base = api.coord([(axis.ymin + axis.ymax) / 2, axis.zmin]);
      // Coordenadas de la fila.
      var yMid = base[1] - 14;
      var x = base[0] - total / 2;
      // Relleno interior de la caja de fondo.
      var padX = 8, padY = 5;
      // Caja gris de fondo redondeada.
      var children = [{
        type: 'rect',
        shape: { x: x - padX, y: yMid - fs / 2 - padY, width: total + 2 * padX, height: fs + 2 * padY, r: 4 },
        style: { fill: UI_BG }, silent: true
      }];
      // Punto de color + etiqueta por cada entrada.
      entries.forEach(function (e) {
        children.push({ type: 'circle', shape: { cx: x + r, cy: yMid, r: r }, style: { fill: colorOf(e.t, cfg.colors), stroke: cfg.markerBorder, lineWidth: 1 }, silent: true });
        children.push({ type: 'text', x: x + 2 * r + 5, y: yMid, style: { text: e.t, fill: '#fff', font: fs + 'px system-ui, sans-serif', textAlign: 'left', textVerticalAlign: 'middle' }, silent: true });
        x += e.w + gap;
      });
      return { type: 'group', children: children };
    };
  }

  /**
   * Dibuja la vista de portería.
   * @param {Object} data Objeto del jugador (player.json) con .Shots
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {ECharts}
   */
  function renderPlayerGoalMap(data, el, opts) {
    // Instancia de ECharts y configuración combinada.
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});
    // Mezcla de colores propios sobre los por defecto.
    if (opts && opts.colors) cfg.colors = Object.assign({}, DEFAULT_COLORS, opts.colors);

    // Instancia (reutilizada si ya existía) y tiros a puerta.
    var chart = ec.getInstanceByDom(el) || ec.init(el);
    var shots = onTargetShots((data && data.Shots) || []);

    // Rango de los ejes (marco + márgenes).
    var axis = {
      ymin: cfg.goalYmin - cfg.marginY, ymax: cfg.goalYmax + cfg.marginY,
      zmin: cfg.goalZmin - cfg.marginZbottom, zmax: cfg.goalZmax + cfg.marginZtop
    };
    // Factor para que el marco conserve la proporción real de la portería.
    var factor = (cfg.realGoalW / cfg.realGoalH) * ((cfg.goalZmax - cfg.goalZmin) / (cfg.goalYmax - cfg.goalYmin));
    // Proporción alto/ancho del área de dibujo.
    var ratioHW = (axis.zmax - axis.zmin) / (factor * (axis.ymax - axis.ymin));

    // Etiquetas para la leyenda.
    var labels = presentLabels(shots);

    // Helper para declarar una serie custom.
    var custom = function (name, ri, z) {
      return { name: name, type: 'custom', coordinateSystem: 'cartesian2d', renderItem: ri, data: [0], silent: true, z: z };
    };

    // Configuración completa del gráfico (GoalY en X, GoalZ en Y con la altura hacia arriba).
    var option = {
      backgroundColor: 'transparent',
      animation: false,
      grid: computeGrid(el, cfg.pad, ratioHW),
      xAxis: { type: 'value', min: axis.ymin, max: axis.ymax, inverse: true, show: false },
      yAxis: { type: 'value', min: axis.zmin, max: axis.zmax, show: false },
      tooltip: cfg.showTooltip ? {
        trigger: 'item', confine: true,
        formatter: function (p) {
          var s = (p.data && p.data._shot) || {};
          return (s.Type || '') + '<br/>Height (Z): ' + Math.round(s.GoalZ) + ' | Y: ' + Math.round(s.GoalY);
        }
      } : { show: false },
      series: [
        custom('__frame__', frameRenderItem(cfg, axis), 1),
        { id: 'shots', name: 'Shots', type: 'scatter', coordinateSystem: 'cartesian2d', symbol: 'circle', data: buildShotData(shots, cfg), z: 5 },
        custom('__legend__', legendRenderItem(cfg, labels, axis), 6)
      ]
    };

    chart.setOption(option, true);

    // Reajuste de tamaño/proporción al redimensionar el contenedor.
    if (!chart.__goalResizeBound) {
      var onResize = function () { chart.resize(); chart.setOption({ grid: computeGrid(el, cfg.pad, ratioHW) }); };
      if (typeof ResizeObserver !== 'undefined') { var ro = new ResizeObserver(onResize); ro.observe(el); chart.__goalResizeObserver = ro; }
      else if (typeof global.addEventListener === 'function') { global.addEventListener('resize', onResize); }
      chart.__goalResizeBound = true;
    }

    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderPlayerGoalMap = renderPlayerGoalMap;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerGoalMap;
  }
})(typeof window !== 'undefined' ? window : this);
