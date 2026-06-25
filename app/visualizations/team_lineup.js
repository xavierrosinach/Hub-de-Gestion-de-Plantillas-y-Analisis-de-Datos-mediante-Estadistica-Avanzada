/**
 * CREACIÓN DE LA ALINEACIÓN DEL EQUIPO SOBRE EL CAMPO CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Proporción largo/ancho de un campo real (105 x 68 m).
  var PITCH_RATIO = 105 / 68;

  // Medidas de las marcas del campo en coordenadas de datos (0-100).
  var M = {penaltyDepthX: (16.5 / 105) * 100, sixDepthX: (5.5 / 105) * 100, penHalfY: (40.32 / 2 / 68) * 100,
           sixHalfY: (18.32 / 2 / 68) * 100, penSpotX: (11 / 105) * 100, goalHalfY: (7.32 / 2 / 68) * 100,
           circleRX: (9.15 / 105) * 100, circleRY: (9.15 / 68) * 100};

  // Opciones por defecto (sobreescribibles con el argumento opts).
  var DEFAULTS = {
    imageBase:    'https://pub-f177abd2266143fa9dc17043d96d50da.r2.dev/images/player/',
    photoR:       24,             // radio del círculo de cada jugador (px)
    ringWidth:    2.5,            // grosor del borde de color de equipo
    pitchColor:   '#1f7a3f',
    lineColor:    'rgba(255,255,255,0.8)',
    lineWidth:    1.4,
    nameColor:    '#1b1b1b',
    nameBg:       'rgba(255,255,255,0.85)',
    mirrorY:      true,
    showLinks:    true,           // dibujar la red de pases (líneas de conexión)
    minPasses:    5,              // pases mínimos para dibujar una conexión
    linkMinWidth: 1,
    linkMaxWidth: 7,
    pad:          12
  };

  // Etiquetas del desplegable y la propiedad de coordenadas que usan.
  var MODES = [
    { label: 'Formation positions', key: 'PositionCoords' },
    { label: "Players' average positions", key: 'PlayerCoords' }
  ];

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[team_lineup] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Calcula los márgenes del grid para centrar el campo con proporción 105:68.
  function computeGrid(el, pad) {
    var W = el.clientWidth || el.offsetWidth || 900;
    var H = el.clientHeight || el.offsetHeight || 580;
    var availW = W - 2 * pad, availH = H - 2 * pad;
    var w, h;
    if (availW / availH > PITCH_RATIO) { h = availH; w = h * PITCH_RATIO; }
    else { w = availW; h = w / PITCH_RATIO; }
    var left = (W - w) / 2, top = (H - h) / 2;
    return { left: left, right: W - left - w, top: top, bottom: H - top - h };
  }

  // Custom renderItem que pinta el rectángulo de césped.
  function grassRenderItem(cfg) {
    return function (params, api) {
      var tl = api.coord([0, 0]), br = api.coord([100, 100]);
      return { type: 'rect', shape: { x: tl[0], y: tl[1], width: br[0] - tl[0], height: br[1] - tl[1] }, style: { fill: cfg.pitchColor }, silent: true };
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
      function line(ax, ay, bx, by, style) {
        var a = P(ax, ay), b = P(bx, by);
        return { type: 'line', shape: { x1: a[0], y1: a[1], x2: b[0], y2: b[1] }, style: style || ls, silent: true };
      }
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

  // Construye los puntos de jugadores según el modo (PositionCoords / PlayerCoords).
  function buildPlayers(lineup, modeKey, cfg) {
    var pts = [];
    lineup.forEach(function (p) {
      var c = p && p[modeKey];
      if (!c || !isNum(c.X) || !isNum(c.Y)) return;
      // Y espejada para que los carriles izquierda/derecha queden bien.
      var y = cfg.mirrorY ? 100 - c.Y : c.Y;
      pts.push({ value: [c.X, y], id: p.Player, name: p.Name || p.Player, position: p.Position || '' });
    });
    return pts;
  }

  // Cuenta los pases entre cada par de jugadores del once (combinando ambos sentidos).
  function buildPassCounts(team, ids) {
    var passes = (team && team.Passes) || [];
    var counts = {};
    passes.forEach(function (p) {
      if (!p || !p.Player || !p.PassReceiver) return;
      if (!ids[p.Player] || !ids[p.PassReceiver]) return;
      // Clave no dirigida (par ordenado alfabéticamente).
      var key = p.Player < p.PassReceiver ? p.Player + '|' + p.PassReceiver : p.PassReceiver + '|' + p.Player;
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  // Color amarillo -> naranja -> rojo según t (0-1): más pases = más rojo.
  function colorYR(t) {
    var stops = [[0, [255, 221, 51]], [0.5, [255, 140, 26]], [1, [215, 25, 28]]];
    for (var i = 1; i < stops.length; i++) {
      if (t <= stops[i][0]) {
        var k = (t - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
        var a = stops[i - 1][1], b = stops[i][1];
        return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * k) + ',' + Math.round(a[1] + (b[1] - a[1]) * k) + ',' + Math.round(a[2] + (b[2] - a[2]) * k) + ')';
      }
    }
    return 'rgb(215,25,28)';
  }

  // Datos de la serie 'lines' de la red de pases, según las posiciones del modo activo.
  function buildLinkData(players, counts, cfg) {
    // Mapas id -> posición y id -> nombre.
    var pos = {}, name = {};
    players.forEach(function (p) { pos[p.id] = p.value; name[p.id] = p.name; });
    // Máximo de pases para escalar grosor y color.
    var max = 0;
    Object.keys(counts).forEach(function (k) { if (counts[k] > max) max = counts[k]; });
    if (max < cfg.minPasses) max = cfg.minPasses;
    var data = [];
    Object.keys(counts).forEach(function (k) {
      var n = counts[k];
      if (n < cfg.minPasses) return;
      var ab = k.split('|');
      if (!pos[ab[0]] || !pos[ab[1]]) return;
      // Grosor y color proporcionales al nº de pases.
      var t = (n - cfg.minPasses) / (max - cfg.minPasses || 1);
      var w = cfg.linkMinWidth + t * (cfg.linkMaxWidth - cfg.linkMinWidth);
      data.push({
        coords: [pos[ab[0]], pos[ab[1]]],
        value: n,
        names: (name[ab[0]] || ab[0]) + ' ↔ ' + (name[ab[1]] || ab[1]),
        lineStyle: { width: w, color: colorYR(t), opacity: 0.9 }
      });
    });
    return data;
  }

  // Custom renderItem de cada jugador: foto recortada en círculo + borde de equipo + nombre.
  function playersRenderItem(players, cfg) {
    return function (params, api) {
      var p = players[params.dataIndex];
      if (!p) return;
      // Centro en píxel y radio.
      var pt = api.coord(p.value);
      var cx = pt[0], cy = pt[1], r = cfg.photoR;
      var url = cfg.imageBase + p.id + '.png';
      return {
        type: 'group',
        children: [
          // Fondo blanco del círculo (capta el ratón para el tooltip).
          { type: 'circle', shape: { cx: cx, cy: cy, r: r }, style: { fill: '#ffffff' } },
          // Foto recortada al círculo.
          { type: 'group', clipPath: { type: 'circle', shape: { cx: cx, cy: cy, r: r - 1 } },
            children: [{ type: 'image', style: { image: url, x: cx - r, y: cy - r, width: 2 * r, height: 2 * r }, silent: true }] },
          // Borde con el color del equipo.
          { type: 'circle', shape: { cx: cx, cy: cy, r: r }, style: { fill: 'none', stroke: cfg.teamColor, lineWidth: cfg.ringWidth }, silent: true },
          // Nombre debajo.
          { type: 'text', x: cx, y: cy + r + 6, silent: true,
            style: { text: p.name, fill: cfg.nameColor, font: '600 11px system-ui, sans-serif', textAlign: 'center', textVerticalAlign: 'top', backgroundColor: cfg.nameBg, padding: [2, 5], borderRadius: 3 } }
        ]
      };
    };
  }

  // Crea el DOM (desplegable + contenedor del campo).
  function buildDom(el) {
    el.innerHTML = '';
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;align-items:center;gap:8px;margin:0 0 8px;font:13px system-ui,sans-serif;color:#222;';
    var label = document.createElement('span');
    label.textContent = 'Positions:';
    var select = document.createElement('select');
    select.style.cssText = 'padding:5px 8px;border:1px solid #ccc;border-radius:4px;font:13px system-ui,sans-serif;';
    MODES.forEach(function (m, i) { var o = document.createElement('option'); o.value = String(i); o.textContent = m.label; select.appendChild(o); });
    controls.appendChild(label); controls.appendChild(select);
    // Selector para mostrar/ocultar la red de pases.
    var linkLabel = document.createElement('label');
    linkLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;margin-left:8px;';
    var linkCb = document.createElement('input');
    linkCb.type = 'checkbox';
    linkCb.checked = true;
    linkLabel.appendChild(linkCb);
    linkLabel.appendChild(document.createTextNode('Show pass connections'));
    controls.appendChild(linkLabel);
    el.appendChild(controls);
    var chartDom = document.createElement('div');
    chartDom.style.cssText = 'width:100%;height:600px;';
    el.appendChild(chartDom);
    return { select: select, linkCb: linkCb, chartDom: chartDom };
  }

  /**
   * Dibuja la alineación del equipo.
   * @param {Object} team Objeto del equipo (team.json) con .Lineup
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {ECharts}
   */
  function renderTeamLineup(team, el, opts) {
    var ec = resolveEcharts(opts);
    var cfg = Object.assign({}, DEFAULTS, opts || {});
    // Color del equipo para los bordes de las fotos.
    cfg.teamColor = (opts && opts.teamColor) || (team && team.PrimaryColour) || '#154284';

    var lineup = (team && team.Lineup) || [];
    var dom = buildDom(el);
    var chart = ec.getInstanceByDom(dom.chartDom) || ec.init(dom.chartDom);

    // IDs del once y conteo de pases entre ellos (no depende del modo).
    var ids = {};
    lineup.forEach(function (p) { if (p && p.Player) ids[p.Player] = true; });
    var passCounts = buildPassCounts(team, ids);

    // Estado del selector de conexiones.
    var showLinks = cfg.showLinks;

    // Helper para declarar una serie custom del campo.
    var custom = function (name, ri, z) {
      return { name: name, type: 'custom', coordinateSystem: 'cartesian2d', renderItem: ri, data: [0], silent: true, z: z };
    };

    // Modo de coordenadas activo.
    var currentKey = MODES[0].key;

    // Dibuja el campo + red de pases + jugadores para un modo de coordenadas.
    function render(modeKey) {
      currentKey = modeKey;
      var players = buildPlayers(lineup, modeKey, cfg);
      var series = [
        custom('__grass__', grassRenderItem(cfg), 1),
        custom('__lines__', linesRenderItem(cfg), 2)
      ];
      // Red de pases (debajo de los jugadores).
      if (showLinks) {
        series.push({
          id: 'links', type: 'lines', coordinateSystem: 'cartesian2d', z: 4,
          polyline: false, lineStyle: { curveness: 0 },
          emphasis: { disabled: true },
          data: buildLinkData(players, passCounts, cfg)
        });
      }
      // Jugadores (custom): foto circular + borde + nombre.
      series.push({ id: 'players', type: 'custom', coordinateSystem: 'cartesian2d', renderItem: playersRenderItem(players, cfg), data: players, z: 6 });

      // Configuración del gráfico: ejes ocultos 0-100 (Y invertida = origen arriba) y campo centrado.
      chart.setOption({
        backgroundColor: 'transparent',
        animation: false,
        grid: computeGrid(el, cfg.pad),
        xAxis: { type: 'value', min: 0, max: 100, show: false },
        yAxis: { type: 'value', min: 0, max: 100, inverse: true, show: false },
        // Tooltip distinto para conexiones de pase (nº de pases) y jugadores (nombre + posición).
        tooltip: {
          trigger: 'item', confine: true,
          formatter: function (p) {
            if (!p.data) return '';
            if (p.seriesId === 'links') return '<b>' + p.data.names + '</b><br/>Passes: ' + p.data.value;
            if (p.seriesId === 'players') return '<b>' + p.data.name + '</b>' + (p.data.position ? '<br/>' + p.data.position : '');
            return '';
          }
        },
        series: series
      }, true);
    }

    // Render inicial (formación) y cambios por los controles.
    render(currentKey);
    dom.select.addEventListener('change', function () { render(MODES[+dom.select.value] ? MODES[+dom.select.value].key : MODES[0].key); });
    dom.linkCb.addEventListener('change', function () { showLinks = dom.linkCb.checked; render(currentKey); });

    // Reajuste al redimensionar.
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(function () { chart.resize(); chart.setOption({ grid: computeGrid(el, cfg.pad) }); }); ro.observe(el);
    } else if (typeof global.addEventListener === 'function') {
      global.addEventListener('resize', function () { chart.resize(); });
    }

    return chart;
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderTeamLineup = renderTeamLineup;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderTeamLineup;
  }
})(typeof window !== 'undefined' ? window : this);
