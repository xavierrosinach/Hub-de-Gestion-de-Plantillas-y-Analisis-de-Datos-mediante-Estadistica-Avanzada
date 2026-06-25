/*
 * CREACIÓN DE UN MAPA DE CALOR A PARTIR DE LOS PASES CON Apache ECharts
 */

(function (global) {'use strict';

  // Proporción largo/ancho de un campo real (105 x 68 m).
  var PITCH_RATIO = 105 / 68;

  // Medidas de las marcas del campo en coordenadas de datos (0-100).
  var M = {penaltyDepthX: (16.5 / 105) * 100, sixDepthX: (5.5 / 105) * 100, penHalfY: (40.32 / 2 / 68) * 100,
           sixHalfY: (18.32 / 2 / 68) * 100, penSpotX: (11 / 105) * 100, goalHalfY: (7.32 / 2 / 68) * 100,
           circleRX: (9.15 / 105) * 100, circleRY: (9.15 / 68) * 100};

  // Paradas del degradado del heatmap: [umbral 0-1, [r,g,b,alfa]].
  var DEFAULT_STOPS = [[0.00, [0, 0, 0, 0]], [0.04, [60, 0, 0, 60]], [0.18, [130, 12, 0, 165]], [0.38, [205, 30, 0, 205]],
                      [0.58, [240, 95, 0, 225]], [0.76, [250, 170, 15, 240]], [0.90, [255, 232, 90, 250]], [1.00, [255, 255, 255, 255]]];

  // Id del elemento de texto de las coordenadas.
  var COORD_ID = 'coordText';

  // Fondo gris semitransparente común a los controles (coordenadas, leyendas, etc.).
  var UI_BG = 'rgba(60,60,60,0.6)';

  // Opciones por defecto (sobreescribibles con el argumento opts).
  var DEFAULTS = {source: 'origin', bandwidth: 7, gridX: 105, gridY: 68, gamma: 0.85, bands: 16, levels: 16, isoColor: 'rgba(255,255,255,0.28)',
                  isoWidth: 1, opacity: 0.92, hiRes: 1050, colorStops: DEFAULT_STOPS, pitchColor: '#1f7a3f', lineColor: 'rgba(255,255,255,0.8)',
                  lineWidth: 1.4, attackColor: 'rgba(255,255,255,0.9)', showAttackLine: true, showAttackLabel: false, showCoords: true,
                  coordColor: '#ffffff', coordFontSize: 13, pitchLengthX: 105, pitchLengthY: 68, onMove: null, pad:12};

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {var ec = (opts && opts.echarts) || global.echarts;
                                 if (!ec) throw new Error('[player_pass_heatmap] ECharts no está disponible.');
                                 return ec;}

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Extrae los puntos para el KDE según la fuente: 'origin', 'end' o 'both'.
  // La Y se espeja (100 - Y): en este dataset el carril derecho son Y bajos,
  // así la banda del jugador queda en el lado correcto del campo dibujado.
  function extractPoints(data, source) {
    var passes = (data && data.Passes) || [];
    var pts = [];
    passes.forEach(function (p) {
      if (!p) return;
      if (source === 'end') {
        if (isNum(p.EndX) && isNum(p.EndY)) pts.push([p.EndX, 100 - p.EndY]);
      } else if (source === 'both') {
        if (isNum(p.IniX) && isNum(p.IniY)) pts.push([p.IniX, 100 - p.IniY]);
        if (isNum(p.EndX) && isNum(p.EndY)) pts.push([p.EndX, 100 - p.EndY]);
      } else {
        if (isNum(p.IniX) && isNum(p.IniY)) pts.push([p.IniX, 100 - p.IniY]);
      }
    });
    return pts;
  }

  // Interpolación lineal entre a y b según t (0-1).
  function lerp(a, b, t) { return a + (b - a) * t; }

  // Color [r,g,b,a] para una densidad d (0-1) interpolando el degradado.
  function colorFor(d, stops) {
    if (d <= stops[0][0]) return stops[0][1];
    for (var i = 1; i < stops.length; i++) {
      if (d <= stops[i][0]) {
        var t = (d - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
        var c0 = stops[i - 1][1], c1 = stops[i][1];
        return [lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t), lerp(c0[3], c1[3], t)];
      }
    }
    return stops[stops.length - 1][1];
  }

  // Calcula el campo escalar normalizado f = (densidad/max)^gamma con un KDE gaussiano.
  function computeField(points, cfg) {
    // Dimensiones de la rejilla y acumulador de densidad.
    var gw = cfg.gridX, gh = cfg.gridY;
    var dens = new Float64Array(gw * gh);
    // Factor del kernel gaussiano: 1 / (2·bandwidth²).
    var inv = 1 / (2 * cfg.bandwidth * cfg.bandwidth);
    var max = 0;
    // Recorremos cada celda de la rejilla (su centro en coords 0-100).
    for (var j = 0; j < gh; j++) {
      var py = (j + 0.5) / gh * 100;
      for (var i = 0; i < gw; i++) {
        var px = (i + 0.5) / gw * 100, s = 0;
        // Sumamos la contribución gaussiana de cada pase a esta celda.
        for (var k = 0; k < points.length; k++) {
          var dx = px - points[k][0], dy = py - points[k][1];
          s += Math.exp(-(dx * dx + dy * dy) * inv);
        }
        dens[j * gw + i] = s;
        if (s > max) max = s;   // Guardamos el máximo para normalizar después.
      }
    }
    // Normalizamos a [0,1] y aplicamos gamma para realzar el contraste.
    var field = new Float64Array(gw * gh);
    for (var n = 0; n < gw * gh; n++) {
      field[n] = max > 0 ? Math.pow(dens[n] / max, cfg.gamma) : 0;
    }
    return { field: field, gw: gw, gh: gh };
  }

  // Segmentos de la isolínea de un nivel mediante marching squares.
  function isolineSegments(field, gw, gh, level) {
    var segs = [];
    // Valor del campo en la celda (i,j).
    function v(i, j) { return field[j * gw + i]; }
    // Recorremos cada celda 2x2 de la rejilla.
    for (var j = 0; j < gh - 1; j++) {
      for (var i = 0; i < gw - 1; i++) {
        // Valores de las cuatro esquinas de la celda.
        var tl = v(i, j), tr = v(i + 1, j), br = v(i + 1, j + 1), bl = v(i, j + 1);
        // Código de 4 bits según qué esquinas superan el nivel.
        var idx = 0;
        if (tl > level) idx |= 8;
        if (tr > level) idx |= 4;
        if (br > level) idx |= 2;
        if (bl > level) idx |= 1;
        // Celda totalmente dentro o fuera: no hay isolínea.
        if (idx === 0 || idx === 15) continue;
        // Interpolación lineal del punto de cruce sobre una arista.
        function ip(va, vb) { var dd = vb - va; return dd === 0 ? 0.5 : (level - va) / dd; }
        // Puntos de cruce en las cuatro aristas (arriba, derecha, abajo, izquierda).
        var a = [i + ip(tl, tr), j];
        var b = [i + 1, j + ip(tr, br)];
        var c = [i + ip(bl, br), j + 1];
        var d = [i, j + ip(tl, bl)];
        // Segmentos a dibujar según la configuración de la celda.
        var e = null;
        switch (idx) {
          case 1:  e = [d, c]; break;
          case 2:  e = [c, b]; break;
          case 3:  e = [d, b]; break;
          case 4:  e = [a, b]; break;
          case 5:  e = [a, b, d, c]; break;
          case 6:  e = [a, c]; break;
          case 7:  e = [a, d]; break;
          case 8:  e = [a, d]; break;
          case 9:  e = [a, c]; break;
          case 10: e = [a, d, c, b]; break;
          case 11: e = [a, b]; break;
          case 12: e = [d, b]; break;
          case 13: e = [c, b]; break;
          case 14: e = [d, c]; break;
        }
        if (e) for (var s = 0; s < e.length; s += 2) segs.push([e[s][0], e[s][1], e[s + 1][0], e[s + 1][1]]);
      }
    }
    return segs;
  }

  // Construye el canvas de alta resolución: relleno por bandas + isolíneas.
  function buildContourCanvas(fieldData, cfg) {
    var field = fieldData.field, gw = fieldData.gw, gh = fieldData.gh;
    var small = document.createElement('canvas');
    small.width = gw; small.height = gh;
    var sctx = small.getContext('2d');
    var img = sctx.createImageData(gw, gh);
    // Nº de bandas para discretizar la densidad (efecto "mapa de niveles").
    var bands = Math.max(1, cfg.bands | 0);
    for (var n = 0; n < gw * gh; n++) {
      // Cuantizamos la densidad a la banda más cercana y le asignamos color.
      var q = Math.round(field[n] * bands) / bands;
      var col = colorFor(q, cfg.colorStops);
      var o = n * 4;
      img.data[o] = col[0]; img.data[o + 1] = col[1]; img.data[o + 2] = col[2]; img.data[o + 3] = col[3];
    }
    sctx.putImageData(img, 0, 0);

    // Canvas grande: relleno escalado suave + isolíneas vectoriales.
    var cw = Math.max(200, cfg.hiRes | 0);
    var ch = Math.round(cw / PITCH_RATIO);
    var hi = document.createElement('canvas');
    hi.width = cw; hi.height = ch;
    var ctx = hi.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(small, 0, 0, cw, ch);

    // Escalas de rejilla a píxel del canvas grande.
    var sx = cw / gw, sy = ch / gh;
    function hx(ci) { return (ci + 0.5) * sx; }
    function hy(cj) { return (cj + 0.5) * sy; }

    // Dibujo de las curvas de nivel.
    ctx.lineWidth = cfg.isoWidth;
    ctx.strokeStyle = cfg.isoColor;
    ctx.lineJoin = 'round';
    var L = Math.max(1, cfg.levels | 0);
    for (var li = 1; li <= L; li++) {
      var level = li / (L + 1);
      var segs = isolineSegments(field, gw, gh, level);
      ctx.beginPath();
      for (var s = 0; s < segs.length; s++) {
        var g = segs[s];
        ctx.moveTo(hx(g[0]), hy(g[1]));
        ctx.lineTo(hx(g[2]), hy(g[3]));
      }
      ctx.stroke();
    }
    return hi;
  }

  // Calcula los márgenes del grid para centrar el campo con proporción 105:68.
  function computeGrid(el, pad) {
    var W = el.clientWidth || el.offsetWidth || 720;
    var H = el.clientHeight || el.offsetHeight || 466;
    var availW = W - 2 * pad, availH = H - 2 * pad;
    var w, h;
    if (availW / availH > PITCH_RATIO) { h = availH; w = h * PITCH_RATIO; }
    else { w = availW; h = w / PITCH_RATIO; }
    var left = (W - w) / 2, top = (H - h) / 2;
    return { left: left, right: W - left - w, top: top, bottom: H - top - h, w: w, h: h };
  }

  // Custom renderItem que pinta el rectángulo de césped.
  function grassRenderItem(cfg) {
    return function (params, api) {
      var tl = api.coord([0, 0]), br = api.coord([100, 100]);
      return { type: 'rect', shape: { x: tl[0], y: tl[1], width: br[0] - tl[0], height: br[1] - tl[1] }, style: { fill: cfg.pitchColor }, silent: true };
    };
  }

  // Custom renderItem que coloca el canvas del heatmap sobre el campo.
  function heatRenderItem(canvas, cfg) {
    return function (params, api) {
      var tl = api.coord([0, 0]), br = api.coord([100, 100]);
      return { type: 'image', style: { image: canvas, x: tl[0], y: tl[1], width: br[0] - tl[0], height: br[1] - tl[1], opacity: cfg.opacity }, silent: true };
    };
  }

  // Custom renderItem que dibuja las líneas del campo (horizontal, ataque a la derecha).
  function linesRenderItem(cfg) {
    return function (params, api) {
      var P = function (dx, dy) { return api.coord([dx, dy]); };
      var ls = { stroke: cfg.lineColor, lineWidth: cfg.lineWidth, fill: 'none' };
      var children = [];
      function rect(ax, ay, bx, by) {
        var a = P(ax, ay), b = P(bx, by);
        return { type: 'rect', shape: { x: Math.min(a[0], b[0]), y: Math.min(a[1], b[1]), width: Math.abs(b[0] - a[0]), height: Math.abs(b[1] - a[1]) }, style: ls, silent: true };
      }
      // Línea entre dos puntos.
      function line(ax, ay, bx, by, style) {
        var a = P(ax, ay), b = P(bx, by);
        return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: style || ls, silent: true };
      }
      // Borde exterior y línea de medio campo.
      children.push(rect(0, 0, 100, 100));
      children.push(line(50, 0, 50, 100));
      var c = P(50, 50);
      var rx = Math.abs(P(50 + M.circleRX, 50)[0] - c[0]);
      var ry = Math.abs(P(50, 50 + M.circleRY)[1] - c[1]);
      children.push({ type: 'ellipse', shape: { cx: c[0], cy: c[1], rx: rx, ry: ry }, style: ls, silent: true });
      children.push({ type: 'circle', shape: { cx: c[0], cy: c[1], r: 2 }, style: { fill: cfg.lineColor }, silent: true });
      children.push(rect(0, 50 - M.penHalfY, M.penaltyDepthX, 50 + M.penHalfY));
      children.push(rect(0, 50 - M.sixHalfY, M.sixDepthX, 50 + M.sixHalfY));
      children.push({ type: 'circle', shape: { cx: P(M.penSpotX, 50)[0], cy: P(M.penSpotX, 50)[1], r: 2 }, style: { fill: cfg.lineColor }, silent: true });
      children.push(line(0, 50 - M.goalHalfY, 0, 50 + M.goalHalfY, { stroke: cfg.lineColor, lineWidth: cfg.lineWidth * 2.2, fill: 'none' }));
      children.push(rect(100, 50 - M.penHalfY, 100 - M.penaltyDepthX, 50 + M.penHalfY));
      children.push(rect(100, 50 - M.sixHalfY, 100 - M.sixDepthX, 50 + M.sixHalfY));
      children.push({ type: 'circle', shape: { cx: P(100 - M.penSpotX, 50)[0], cy: P(100 - M.penSpotX, 50)[1], r: 2 }, style: { fill: cfg.lineColor }, silent: true });
      children.push(line(100, 50 - M.goalHalfY, 100, 50 + M.goalHalfY, { stroke: cfg.lineColor, lineWidth: cfg.lineWidth * 2.2, fill: 'none' }));
      return { type: 'group', children: children };
    };
  }

  // Serie 'lines' con la flecha que indica la dirección de ataque.
  function buildAttackSeries(cfg) {
    if (!cfg.showAttackLine) return [];
    var arrow = {
      name: '__attack__', type: 'lines', coordinateSystem: 'cartesian2d',
      symbol: ['none', 'arrow'], symbolSize: 11,
      lineStyle: { color: cfg.attackColor, width: 2, opacity: 0.9 },
      silent: true, data: [{ coords: [[40, 5.5], [62, 5.5]] }], z: 6
    };
    if (cfg.showAttackLabel) {
      arrow.label = { show: true, position: 'middle', formatter: 'ATTACK', color: cfg.attackColor, fontSize: 10, fontWeight: 'bold', offset: [0, -9] };
    }
    return [arrow];
  }

  // Elemento de texto (graphic) de las coordenadas, con fondo gris, anclado arriba-izquierda del campo.
  function coordGraphic(grid, cfg) {
    return {
      type: 'text',
      id: COORD_ID,
      left: grid.left + 8,
      top: grid.top + 8,
      z: 100,
      silent: true,
      invisible: true,
      style: {
        text: '',
        fill: cfg.coordColor,
        fontSize: cfg.coordFontSize,
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        backgroundColor: UI_BG,
        padding: [3, 7],
        borderRadius: 4
      }
    };
  }

  // Conecta el movimiento del ratón para mostrar las coordenadas (en metros) dentro del campo.
  function bindCoordReadout(chart, cfg) {
    if (chart.__coordReadoutBound) return;
    var zr = chart.getZr();
    var show = function (txt) {
      if (cfg.showCoords) chart.setOption({ graphic: [{ id: COORD_ID, invisible: false, style: { text: txt } }] });
    };
    var hide = function () {
      if (cfg.showCoords) chart.setOption({ graphic: [{ id: COORD_ID, invisible: true, style: { text: '' } }] });
    };
    zr.on('mousemove', function (e) {
      var p = [e.offsetX, e.offsetY];
      if (chart.containPixel({ gridIndex: 0 }, p)) {
        var dc = chart.convertFromPixel({ gridIndex: 0 }, p);
        var x = dc[0], y = dc[1];
        if (x >= 0 && x <= 100 && y >= 0 && y <= 100) {
          var mx = Math.round(x / 100 * cfg.pitchLengthX);
          var my = Math.round(y / 100 * cfg.pitchLengthY);
          show('X: ' + mx + ' m  |  Y: ' + my + ' m');
          if (typeof cfg.onMove === 'function') cfg.onMove({ x: x, y: y, mx: mx, my: my });
          return;
        }
      }
      hide();
      if (typeof cfg.onMove === 'function') cfg.onMove(null);
    });
    zr.on('globalout', function () {
      hide();
      if (typeof cfg.onMove === 'function') cfg.onMove(null);
    });
    chart.__coordReadoutBound = true;
  }

  // Dibuja el mapa de calor de pases del jugador sobre el campo.
  function renderPlayerPassHeatmap(data, el, opts) {
    // Instancia de ECharts y configuración combinada.
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});

    // Instancia (reutilizada si ya existía), puntos del KDE y canvas del heatmap.
    var chart = ec.getInstanceByDom(el) || ec.init(el);
    var points = extractPoints(data, cfg.source);
    var canvas = buildContourCanvas(computeField(points, cfg), cfg);
    var grid = computeGrid(el, cfg.pad);

    // Helper para declarar una serie custom.
    var custom = function (name, renderItem, z) {
      return { name: name, type: 'custom', coordinateSystem: 'cartesian2d', renderItem: renderItem, data: [0], silent: true, z: z };
    };

    // Configuración completa del gráfico.
    var option = {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: grid.left, right: grid.right, top: grid.top, bottom: grid.bottom },
      xAxis: { type: 'value', min: 0, max: 100, show: false },
      yAxis: { type: 'value', min: 0, max: 100, inverse: true, show: false },
      tooltip: { show: false },
      graphic: [coordGraphic(grid, cfg)],
      series: [
        custom('__grass__', grassRenderItem(cfg), 1),
        custom('__heat__', heatRenderItem(canvas, cfg), 2),
        custom('__lines__', linesRenderItem(cfg), 3)
      ].concat(buildAttackSeries(cfg))
    };

    chart.setOption(option, true);

    // Reajuste al redimensionar: recalcula el grid (campo centrado) y reposiciona el texto de coords.
    if (!chart.__heatResizeBound) {
      var onResize = function () {
        chart.resize();
        var g = computeGrid(el, cfg.pad);
        chart.setOption({
          grid: { left: g.left, right: g.right, top: g.top, bottom: g.bottom },
          graphic: [{ id: COORD_ID, left: g.left + 8, top: g.top + 8 }]
        });
      };
      if (typeof ResizeObserver !== 'undefined') {
        var ro = new ResizeObserver(onResize); ro.observe(el); chart.__heatResizeObserver = ro;
      } else if (typeof global.addEventListener === 'function') {
        global.addEventListener('resize', onResize);
      }
      chart.__heatResizeBound = true;
    }

    // Activa el lector de coordenadas.
    bindCoordReadout(chart, cfg);
    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderPlayerPassHeatmap = renderPlayerPassHeatmap;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerPassHeatmap;
  }
})(typeof window !== 'undefined' ? window : this);
