/**
 * CREACIÓN DE UN MAPA DE TIROS CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Fondo gris semitransparente común a checkbox, leyenda y coordenadas.
  var UI_BG = 'rgba(60,60,60,0.6)';

  // Medidas de las marcas del campo en coordenadas de datos (0-100), salvo circleR en metros.
  var M = {
    penaltyDepthX: (16.5 / 105) * 100,
    sixDepthX:     (5.5  / 105) * 100,
    penHalfY:      (40.32 / 2 / 68) * 100,
    sixHalfY:      (18.32 / 2 / 68) * 100,
    penSpotX:      (11   / 105) * 100,
    goalHalfY:     (7.32 / 2 / 68) * 100,
    circleR:       9.15
  };

  // Color por tipo de tiro
  var DEFAULT_COLORS = {
    'Goal':       '#ffd400',
    'Saved Shot': '#36b3ff',
    'Miss':       '#ff5252',
    'Blocked':    '#ff9800',
    'Post':       '#b388ff',
    'Penalty':    '#ffd400',
    'Own Goal':   '#ff5252',
    '_default':   '#e0e0e0'
  };

  // Opciones por defecto
  var DEFAULTS = {
    halfPitch:    true,
    colors:       DEFAULT_COLORS,
    shotSize:     10,
    goalSize:     17,
    markerBorder: 'rgba(0,0,0,0.55)',
    markerBorderWidth: 1,
    pitchColor:   '#1f7a3f',
    lineColor:    'rgba(255,255,255,0.8)',
    lineWidth:    1.4,
    arrowWidth:   1.6,
    showArrows:   false,
    showArrowToggle: true,
    arrowLabel:   'Show shot direction',
    showLegend:   true,
    legendFontSize: 12,
    legendDotR:   6,
    showTooltip:  true,
    pitchLengthX: 105,
    pitchLengthY: 68,
    pad:          12
  };

  // Devuelve la instancia de ECharts o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[player_shot_map] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Color correspondiente a un tipo de tiro.
  function colorOf(type, colors) {
    return (colors && colors[type]) || colors._default || '#e0e0e0';
  }

  // Punto final del tiro sobre el césped (bloqueo, o cruce de la línea de gol en X=100).
  function shotEnd(s) {
    if (isNum(s.BlockX) && isNum(s.BlockY)) return [s.BlockY, s.BlockX];
    if (isNum(s.GoalY)) return [s.GoalY, 100];
    return null;
  }

  // Calcula los márgenes del grid para centrar el campo manteniendo su proporción (alto/ancho).
  function computeGrid(el, pad, ratioHW) {
    var W = el.clientWidth || el.offsetWidth || 620;
    var H = el.clientHeight || el.offsetHeight || 480;
    var availW = W - 2 * pad, availH = H - 2 * pad;
    var w, h;
    if (availW * ratioHW <= availH) { w = availW; h = w * ratioHW; }
    else { h = availH; w = h / ratioHW; }
    var left = (W - w) / 2, top = (H - h) / 2;
    return { left: left, right: W - left - w, top: top, bottom: H - top - h };
  }

  // Custom renderItem que pinta el rectángulo de césped del campo.
  function grassRenderItem(cfg, xmin) {
    return function (params, api) {
      var bl = api.coord([0, xmin]), tr = api.coord([100, 100]);
      var x = Math.min(bl[0], tr[0]), y = Math.min(bl[1], tr[1]);
      return { type: 'rect', shape: { x: x, y: y, width: Math.abs(tr[0] - bl[0]), height: Math.abs(tr[1] - bl[1]) }, style: { fill: cfg.pitchColor }, silent: true };
    };
  }

  // Custom renderItem que dibuja las líneas del campo (vertical, portería arriba).
  function linesRenderItem(cfg, xmin) {
    return function (params, api) {
      var P = function (dx, dy) { return api.coord([dy, dx]); };
      var ls = { stroke: cfg.lineColor, lineWidth: cfg.lineWidth, fill: 'none' };
      var children = [];

      // Rectángulo entre dos esquinas (en coords de datos).
      function rect(ax, ay, bx, by) {
        var a = P(ax, ay), b = P(bx, by);
        return { type: 'rect', shape: { x: Math.min(a[0], b[0]), y: Math.min(a[1], b[1]), width: Math.abs(b[0] - a[0]), height: Math.abs(b[1] - a[1]) }, style: ls, silent: true };
      }

      // Línea entre dos puntos (en coords de datos).
      function line(ax, ay, bx, by, style) {
        var a = P(ax, ay), b = P(bx, by);
        return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: style || ls, silent: true };
      }

      // Punto/lunar pequeño (penaltis y centro).
      function spot(dx, dy) {
        var p = P(dx, dy);
        return { type: 'circle', shape: { cx: p[0], cy: p[1], r: 2 }, style: { fill: cfg.lineColor }, silent: true };
      }

      // Arco como polilínea: círculo real (m) convertido a elipse en datos.
      function arc(cx, cy, rM, a0, a1, n) {
        var ax = rM / cfg.pitchLengthX * 100, ay = rM / cfg.pitchLengthY * 100, pts = [];
        for (var k = 0; k <= n; k++) {
          var t = a0 + (a1 - a0) * k / n;
          pts.push(P(cx + ax * Math.cos(t), cy + ay * Math.sin(t)));
        }
        return { type: 'polyline', shape: { points: pts }, style: ls, silent: true };
      }
      // Conversión grados -> radianes.
      var D2R = Math.PI / 180;

      // Borde del campo (medio campo si halfPitch) y línea de fondo/medio.
      children.push(rect(xmin, 0, 100, 100));
      if (xmin > 0) children.push(line(xmin, 0, xmin, 100));
      else children.push(line(50, 0, 50, 100));

      // Área de penalti, área pequeña, punto de penalti, arco y línea de gol (portería de arriba).
      children.push(rect(100 - M.penaltyDepthX, 50 - M.penHalfY, 100, 50 + M.penHalfY));
      children.push(rect(100 - M.sixDepthX, 50 - M.sixHalfY, 100, 50 + M.sixHalfY));
      children.push(spot(100 - M.penSpotX, 50));
      children.push(arc(100 - M.penSpotX, 50, M.circleR, 126.87 * D2R, 233.13 * D2R, 28));
      children.push(line(100, 50 - M.goalHalfY, 100, 50 + M.goalHalfY, { stroke: cfg.lineColor, lineWidth: cfg.lineWidth * 2.4, fill: 'none' }));

      // Medio campo: solo el arco central; campo completo: además la portería de abajo.
      if (xmin > 0) {
        children.push(arc(50, 50, M.circleR, -90 * D2R, 90 * D2R, 28));
        children.push(spot(50, 50));
      } else {
        children.push(arc(50, 50, M.circleR, 0, 360 * D2R, 48));
        children.push(spot(50, 50));
        children.push(rect(0, 50 - M.penHalfY, M.penaltyDepthX, 50 + M.penHalfY));
        children.push(rect(0, 50 - M.sixHalfY, M.sixDepthX, 50 + M.sixHalfY));
        children.push(spot(M.penSpotX, 50));
        children.push(arc(M.penSpotX, 50, M.circleR, -53.13 * D2R, 53.13 * D2R, 28));
        children.push(line(0, 50 - M.goalHalfY, 0, 50 + M.goalHalfY, { stroke: cfg.lineColor, lineWidth: cfg.lineWidth * 2.4, fill: 'none' }));
      }

      return { type: 'group', children: children };
    };
  }

  // Construye los puntos del scatter (inicio del tiro), con color y tamaño por tipo.
  function buildShotData(shots, cfg) {
    var pts = [];
    shots.forEach(function (s) {
      if (!s || !isNum(s.IniX) || !isNum(s.IniY)) return;
      var isGoal = s.Type === 'Goal';
      pts.push({
        value: [s.IniY, s.IniX],
        name: s.Type,
        symbolSize: isGoal ? cfg.goalSize : cfg.shotSize,
        itemStyle: { color: colorOf(s.Type, cfg.colors), borderColor: cfg.markerBorder, borderWidth: cfg.markerBorderWidth },
        _shot: s
      });
    });
    return pts;
  }

  // Construye las flechas (inicio -> final) para la serie 'lines'.
  function buildArrowData(shots, cfg) {
    var arr = [];
    shots.forEach(function (s) {
      if (!s || !isNum(s.IniX) || !isNum(s.IniY)) return;
      var end = shotEnd(s);
      if (!end) return;
      arr.push({ coords: [[s.IniY, s.IniX], end], lineStyle: { color: colorOf(s.Type, cfg.colors) } });
    });
    return arr;
  }

  // Lista de tipos de tiro presentes, ordenados según colores
  function presentTypes(shots, cfg) {
    var seen = {}, present = [];
    shots.forEach(function (s) { if (s && s.Type && !seen[s.Type]) { seen[s.Type] = 1; present.push(s.Type); } });
    var order = Object.keys(cfg.colors).filter(function (k) { return k !== '_default'; });
    return order.filter(function (t) { return seen[t]; })
      .concat(present.filter(function (t) { return order.indexOf(t) < 0; }));
  }

  // Custom renderItem de la leyenda: caja gris + punto de color y nombre por tipo, abajo del campo.
  function legendRenderItem(cfg, types, xmin) {
    return function (params, api) {
      if (!cfg.showLegend || !types.length) return;
      var fs = cfg.legendFontSize, r = cfg.legendDotR, gap = 18, charW = fs * 0.6;
      var entries = types.map(function (t) { return { t: t, w: 2 * r + 5 + t.length * charW }; });
      var total = entries.reduce(function (a, e) { return a + e.w; }, 0) + gap * (entries.length - 1);
      var base = api.coord([50, xmin]);
      var yMid = base[1] - 16;
      var x = base[0] - total / 2;
      var padX = 8, padY = 5;
      var children = [{
        type: 'rect',
        shape: { x: x - padX, y: yMid - fs / 2 - padY, width: total + 2 * padX, height: fs + 2 * padY, r: 4 },
        style: { fill: UI_BG }, silent: true
      }];
      entries.forEach(function (e) {
        children.push({ type: 'circle', shape: { cx: x + r, cy: yMid, r: r }, style: { fill: colorOf(e.t, cfg.colors), stroke: cfg.markerBorder, lineWidth: 1 }, silent: true });
        children.push({ type: 'text', x: x + 2 * r + 5, y: yMid, style: { text: e.t, fill: '#fff', font: fs + 'px system-ui, sans-serif', textAlign: 'left', textVerticalAlign: 'middle' }, silent: true });
        x += e.w + gap;
      });
      return { type: 'group', children: children };
    };
  }

  // Crea el checkbox "Show shot direction" para mostrar las líneas de tiro.
  function ensureToggle(el, chart, cfg) {
    if (!cfg.showArrowToggle || chart.__shotToggle) return;
    if (global.getComputedStyle && global.getComputedStyle(el).position === 'static') el.style.position = 'relative';
    var label = document.createElement('label');
    label.style.cssText = 'position:absolute;top:8px;right:8px;z-index:10;display:flex;align-items:center;gap:6px;background:' + UI_BG + ';color:#fff;font:12px system-ui,sans-serif;padding:4px 8px;border-radius:4px;cursor:pointer;user-select:none;';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = !!cfg.showArrows;
    cb.style.cursor = 'pointer';
    var span = document.createElement('span');
    span.textContent = cfg.arrowLabel;
    label.appendChild(cb);
    label.appendChild(span);
    el.appendChild(label);
    cb.addEventListener('change', function () { chart.setArrowsVisible(cb.checked); });
    chart.__shotToggle = label;
  }

  // Dibuja el mapa de tiros del jugador.
  function renderPlayerShotMap(data, el, opts) {
    // Instancia de ECharts y configuración combinada (colores fusionados con los por defecto).
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});
    if (opts && opts.colors) cfg.colors = Object.assign({}, DEFAULT_COLORS, opts.colors);

    // Instancia, tiros y límites del campo (medio campo si halfPitch).
    var chart = ec.getInstanceByDom(el) || ec.init(el);
    var shots = (data && data.Shots) || [];
    var xmin = cfg.halfPitch ? 50 : 0;
    var ratioHW = ((100 - xmin) / 100 * cfg.pitchLengthX) / cfg.pitchLengthY;

    // Flechas de dirección (se guardan para el toggle) y tipos presentes para la leyenda.
    var arrowData = buildArrowData(shots, cfg);
    chart.__arrowData = arrowData;
    var types = presentTypes(shots, cfg);

    // Helper para declarar una serie custom.
    var custom = function (name, ri, z) {
      return { name: name, type: 'custom', coordinateSystem: 'cartesian2d', renderItem: ri, data: [0], silent: true, z: z };
    };

    // Configuración completa del gráfico.
    var option = {
      backgroundColor: 'transparent',
      animation: false,
      grid: computeGrid(el, cfg.pad, ratioHW),
      xAxis: { type: 'value', min: 0, max: 100, inverse: true, show: false },
      yAxis: { type: 'value', min: xmin, max: 100, show: false },
      tooltip: cfg.showTooltip ? {
        trigger: 'item', confine: true,
        formatter: function (p) {
          if (p.seriesId === 'arrows') return '';
          var s = (p.data && p.data._shot) || {};
          var mx = isNum(s.IniX) ? Math.round(s.IniX / 100 * cfg.pitchLengthX) : '-';
          var my = isNum(s.IniY) ? Math.round(s.IniY / 100 * cfg.pitchLengthY) : '-';
          return (s.Type || '') + '<br/>Start X: ' + mx + ' m | Y: ' + my + ' m';
        }
      } : { show: false },
      series: [
        custom('__grass__', grassRenderItem(cfg, xmin), 1),
        custom('__lines__', linesRenderItem(cfg, xmin), 2),
        {
          id: 'arrows', name: cfg.arrowLabel, type: 'lines', coordinateSystem: 'cartesian2d',
          symbol: ['none', 'arrow'], symbolSize: 8,
          lineStyle: { width: cfg.arrowWidth, opacity: 0.85 },
          data: cfg.showArrows ? arrowData : [],
          z: 5
        },
        {
          id: 'shots', name: 'Shots', type: 'scatter', coordinateSystem: 'cartesian2d',
          symbol: 'circle', data: buildShotData(shots, cfg), z: 6
        },
        custom('__legend__', legendRenderItem(cfg, types, xmin), 7)
      ]
    };

    chart.setOption(option, true);

    // Método para mostrar u ocultar las flechas de dirección.
    chart.setArrowsVisible = function (v) {
      chart.setOption({ series: [{ id: 'arrows', data: v ? chart.__arrowData : [] }] });
    };

    // Reajuste de tamaño/proporción al redimensionar el contenedor.
    if (!chart.__shotResizeBound) {
      var onResize = function () { chart.resize(); chart.setOption({ grid: computeGrid(el, cfg.pad, ratioHW) }); };
      if (typeof ResizeObserver !== 'undefined') { var ro = new ResizeObserver(onResize); ro.observe(el); chart.__shotResizeObserver = ro; }
      else if (typeof global.addEventListener === 'function') { global.addEventListener('resize', onResize); }
      chart.__shotResizeBound = true;
    }

    // Crea el selector de dirección.
    ensureToggle(el, chart, cfg);
    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderPlayerShotMap = renderPlayerShotMap;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerShotMap;
  }
})(typeof window !== 'undefined' ? window : this);
