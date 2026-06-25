/**
 * CREACIÓN DE 3 RADAR CHARTS DE PERCENTILES POR POSICIÓN CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Colores de cada serie (jugador, media de similares, jugador comparado).
  var COLORS = { player: '#154284', similar: '#EDBB00', compared: '#9d1009' };

  // Convierte un color hex (#rgb o #rrggbb) a rgba con la opacidad indicada.
  function hexRgba(hex, a) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  // Grupos de 6 métricas por posición (3 grupos -> 3 radares).
  var GROUPINGS = {
    GK: [
      { name: 'Distribution', metrics: ['PassesPer90', 'PassAccuracy', 'LongBallAccuracy', 'OwnHalfPassAccuracy', 'ProgressiveFieldTilt', 'PassesPerTouch'] },
      { name: 'Shot Stopping', metrics: ['SavesPer90', 'SaveRate', 'SavedShotsInsideBoxRate', 'GoalsConcededPer90', 'GoalsPreventedPer90', 'CleanSheetsPer90'] },
      { name: 'Sweeping & Claims', metrics: ['KeeperSweeperActionsPer90', 'KeeperSweeperAccuracy', 'HighClaimsPer90', 'HighClaimRate', 'PunchRate', 'PenaltySaveRate'] }
    ],
    CB: [
      { name: 'Passing', metrics: ['PassesPer90', 'PassAccuracy', 'OwnHalfPassAccuracy', 'OppositionHalfPassAccuracy', 'ProgressiveFieldTilt', 'LongBallAccuracy'] },
      { name: 'Defending', metrics: ['TacklesPer90', 'TackleAccuracy', 'InterceptionsPer90', 'ClearancesPer90', 'OutfielderBlocksPer90', 'BallRecoveriesPer90'] },
      { name: 'Duels', metrics: ['DuelsWonPer90', 'DuelWinRate', 'AerialWonPer90', 'AerialWinRate', 'DefensiveActionsPer90', 'DefensiveActionSuccess'] }
    ],
    LB: [
      { name: 'Passing', metrics: ['PassesPer90', 'PassAccuracy', 'OppositionHalfPassAccuracy', 'ProgressiveFieldTilt', 'PassPercDirForward', 'LongBallAccuracy'] },
      { name: 'Attacking', metrics: ['CrossesPer90', 'CrossAccuracy', 'KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90'] },
      { name: 'Defending', metrics: ['TacklesPer90', 'TackleAccuracy', 'InterceptionsPer90', 'DuelsWonPer90', 'DuelWinRate', 'BallRecoveriesPer90'] }
    ],
    RB: [
      { name: 'Passing', metrics: ['PassesPer90', 'PassAccuracy', 'OppositionHalfPassAccuracy', 'ProgressiveFieldTilt', 'PassPercDirForward', 'LongBallAccuracy'] },
      { name: 'Attacking', metrics: ['CrossesPer90', 'CrossAccuracy', 'KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90'] },
      { name: 'Defending', metrics: ['TacklesPer90', 'TackleAccuracy', 'InterceptionsPer90', 'DuelsWonPer90', 'DuelWinRate', 'BallRecoveriesPer90'] }
    ],
    DM: [
      { name: 'Passing', metrics: ['PassesPer90', 'PassAccuracy', 'OppositionHalfPassAccuracy', 'ProgressiveFieldTilt', 'PassPercDirForward', 'LongBallAccuracy'] },
      { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90', 'AssistConversion', 'OppositionHalfPassShare'] },
      { name: 'Defending', metrics: ['TacklesPer90', 'TackleAccuracy', 'InterceptionsPer90', 'DuelsWonPer90', 'DuelWinRate', 'BallRecoveriesPer90'] }
    ],
    AM: [
      { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90', 'AssistConversion', 'KeyPassesPerPass'] },
      { name: 'Finishing', metrics: ['TotalShotsPer90', 'ShotsOnTargetPer90', 'GoalsPer90', 'ExpectedGoalsPer90', 'GoalConversion', 'ShotAccuracy'] },
      { name: 'Possession', metrics: ['PassesPer90', 'PassAccuracy', 'ProgressiveFieldTilt', 'ContestsPer90', 'ContestWinRate', 'WasFouledPer90'] }
    ],
    LW: [
      { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90', 'CrossesPer90', 'CrossAccuracy'] },
      { name: 'Finishing', metrics: ['TotalShotsPer90', 'ShotsOnTargetPer90', 'GoalsPer90', 'ExpectedGoalsPer90', 'GoalConversion', 'ShotAccuracy'] },
      { name: 'Dribbling', metrics: ['ContestsPer90', 'ContestWinRate', 'PassesPer90', 'PassAccuracy', 'ProgressiveFieldTilt', 'WasFouledPer90'] }
    ],
    RW: [
      { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90', 'CrossesPer90', 'CrossAccuracy'] },
      { name: 'Finishing', metrics: ['TotalShotsPer90', 'ShotsOnTargetPer90', 'GoalsPer90', 'ExpectedGoalsPer90', 'GoalConversion', 'ShotAccuracy'] },
      { name: 'Dribbling', metrics: ['ContestsPer90', 'ContestWinRate', 'PassesPer90', 'PassAccuracy', 'ProgressiveFieldTilt', 'WasFouledPer90'] }
    ],
    ST: [
      { name: 'Finishing', metrics: ['TotalShotsPer90', 'ShotsOnTargetPer90', 'GoalsPer90', 'ExpectedGoalsPer90', 'GoalConversion', 'GoalsPerShotOnTarget'] },
      { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'GoalAssistsPer90', 'AssistConversion', 'PassAccuracy'] },
      { name: 'Aerial & Hold-up', metrics: ['AerialWonPer90', 'AerialWinRate', 'DuelsWonPer90', 'DuelWinRate', 'WasFouledPer90', 'TouchesPer90'] }
    ]
  };

  // Etiquetas cortas para los ejes (fallback: humanizar el nombre).
  var LABELS = {
    PassesPer90: 'Passes/90', PassAccuracy: 'Pass %', OwnHalfPassAccuracy: 'Own½ Pass %', OppositionHalfPassAccuracy: 'Opp½ Pass %',
    OppositionHalfPassShare: 'Opp½ Share', ProgressiveFieldTilt: 'Field Tilt', LongBallAccuracy: 'Long Ball %', PassPercDirForward: 'Fwd Pass %',
    PassesPerTouch: 'Pass/Touch', TouchesPer90: 'Touches/90', KeyPassesPer90: 'Key Passes/90', KeyPassesPerPass: 'Key Pass Ratio',
    ExpectedAssistsPer90: 'xA/90', BigChancesCreatedPer90: 'Big Chances/90', GoalAssistsPer90: 'Assists/90', AssistConversion: 'Assist Conv.',
    CrossesPer90: 'Crosses/90', CrossAccuracy: 'Cross %', TotalShotsPer90: 'Shots/90', ShotsOnTargetPer90: 'SoT/90', ShotAccuracy: 'Shot Acc.',
    GoalsPer90: 'Goals/90', ExpectedGoalsPer90: 'xG/90', GoalConversion: 'Goal Conv.', GoalsPerShotOnTarget: 'Goals/SoT',
    TacklesPer90: 'Tackles/90', TackleAccuracy: 'Tackle %', InterceptionsPer90: 'Intercept./90', ClearancesPer90: 'Clearances/90',
    OutfielderBlocksPer90: 'Blocks/90', BallRecoveriesPer90: 'Recoveries/90', DuelsWonPer90: 'Duels Won/90', DuelWinRate: 'Duel %',
    AerialWonPer90: 'Aerials Won/90', AerialWinRate: 'Aerial %', DefensiveActionsPer90: 'Def Actions/90', DefensiveActionSuccess: 'Def Success',
    ContestsPer90: 'Dribbles/90', ContestWinRate: 'Dribble %', WasFouledPer90: 'Fouled/90', SavesPer90: 'Saves/90', SaveRate: 'Save %',
    SavedShotsInsideBoxRate: 'Box Save %', GoalsConcededPer90: 'Conceded/90', GoalsPreventedPer90: 'Goals Prev./90', CleanSheetsPer90: 'Clean Sheets/90',
    KeeperSweeperActionsPer90: 'Sweeper/90', KeeperSweeperAccuracy: 'Sweeper %', HighClaimsPer90: 'High Claims/90', HighClaimRate: 'Claim %',
    PunchRate: 'Punch %', PenaltySaveRate: 'Pen Save %'
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[player_radar_charts] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Etiqueta legible de una métrica.
  function labelOf(m) { return LABELS[m] || m.replace(/Per90/, '/90').replace(/([a-z])([A-Z])/g, '$1 $2'); }

  // Valor de percentil de una métrica (0 si falta).
  function pv(obj, m) { return obj && isNum(obj[m]) ? obj[m] : 0; }

  // Localiza la posición del jugador dentro de la estructura de comparación.
  function findPosition(player, comparison) {
    var id = player && player.ID;
    // Prioriza FirstPos / SecondPos si el jugador está allí.
    var prefs = [player && player.FirstPos, player && player.SecondPos];
    for (var i = 0; i < prefs.length; i++) {
      var p = prefs[i];
      if (p && comparison[p] && comparison[p].Percentiles && comparison[p].Percentiles[id]) return p;
    }
    // Si no, busca en todas las posiciones.
    var keys = Object.keys(comparison);
    for (var k = 0; k < keys.length; k++) {
      var pc = comparison[keys[k]].Percentiles;
      if (pc && pc[id]) return keys[k];
    }
    return null;
  }

  // Media de percentiles de los SimilarPlayers presentes en la misma posición.
  function similarMean(player, percentiles, groups) {
    var sims = (player && player.SimilarPlayers) || [];
    // Métricas únicas de los 3 grupos.
    var metrics = {};
    groups.forEach(function (g) { g.metrics.forEach(function (m) { metrics[m] = true; }); });
    var keys = Object.keys(metrics);
    // Percentiles de los similares encontrados.
    var rows = [];
    sims.forEach(function (s) {
      var pc = percentiles[s.Player];
      if (pc) rows.push(pc);
    });
    if (!rows.length) return null;
    // Media por métrica.
    var out = {};
    keys.forEach(function (m) {
      var sum = 0, c = 0;
      rows.forEach(function (r) { if (isNum(r[m])) { sum += r[m]; c++; } });
      out[m] = c ? sum / c : 0;
    });
    return out;
  }

  // Lista {id, name} de jugadores de la misma posición (para el buscador).
  function samePositionPlayers(percentiles, excludeId) {
    return Object.keys(percentiles)
      .filter(function (id) { return id !== excludeId; })
      .map(function (id) { return { id: id, name: percentiles[id].Name || id }; })
      .sort(function (a, b) { return a.name.localeCompare(b.name); });
  }

  // Crea el DOM (controles + 3 contenedores de radar) dentro de el.
  function buildDom(el, players, opts) {
    el.innerHTML = '';
    // Controles superiores.
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;margin:0 0 8px;font:13px system-ui,sans-serif;color:#222;';
    // Checkbox de similares.
    var simLabel = document.createElement('label');
    simLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;';
    var simCb = document.createElement('input');
    simCb.type = 'checkbox';
    simLabel.appendChild(simCb);
    simLabel.appendChild(document.createTextNode('Show mean percentiles of similar players'));
    // Buscador de jugador.
    var searchWrap = document.createElement('div');
    searchWrap.style.cssText = 'display:flex;align-items:center;gap:6px;';
    var input = document.createElement('input');
    input.setAttribute('list', 'radar-players-' + Math.random().toString(36).slice(2));
    input.placeholder = 'Compare with player (same position)…';
    input.style.cssText = 'padding:5px 8px;border:1px solid #ccc;border-radius:4px;min-width:240px;font:13px system-ui,sans-serif;';
    var datalist = document.createElement('datalist');
    datalist.id = input.getAttribute('list');
    players.forEach(function (p) { var o = document.createElement('option'); o.value = p.name; datalist.appendChild(o); });
    var clearBtn = document.createElement('button');
    clearBtn.textContent = 'Clear';
    clearBtn.style.cssText = 'padding:5px 10px;border:1px solid #ccc;border-radius:4px;background:#f3f3f3;cursor:pointer;';
    searchWrap.appendChild(input);
    searchWrap.appendChild(datalist);
    searchWrap.appendChild(clearBtn);
    controls.appendChild(simLabel);
    controls.appendChild(searchWrap);
    el.appendChild(controls);
    // Fila de los 3 radares.
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;';
    var charts = [];
    for (var i = 0; i < 3; i++) {
      var d = document.createElement('div');
      d.style.cssText = 'flex:1 1 300px;min-width:280px;height:360px;';
      row.appendChild(d);
      charts.push(d);
    }
    el.appendChild(row);
    return { simCb: simCb, input: input, clearBtn: clearBtn, chartDoms: charts };
  }

  // Construye la option de un radar (un grupo de 6 métricas) según el estado.
  function radarOption(group, state) {
    // Indicadores (ejes) del radar.
    var indicator = group.metrics.map(function (m) { return { name: labelOf(m), max: 100 }; });
    // Series visibles.
    var data = [];
    data.push({
      value: group.metrics.map(function (m) { return Math.round(pv(state.player, m)); }),
      name: state.playerName,
      lineStyle: { color: COLORS.player, width: 2 },
      areaStyle: { color: hexRgba(COLORS.player, 0.18) },
      itemStyle: { color: COLORS.player }
    });
    if (state.showSimilar && state.similar) {
      data.push({
        value: group.metrics.map(function (m) { return Math.round(pv(state.similar, m)); }),
        name: 'Similar players (avg)',
        lineStyle: { color: COLORS.similar, width: 2, type: 'dashed' },
        areaStyle: { color: hexRgba(COLORS.similar, 0.12) },
        itemStyle: { color: COLORS.similar }
      });
    }
    if (state.compared) {
      data.push({
        value: group.metrics.map(function (m) { return Math.round(pv(state.compared, m)); }),
        name: state.comparedName,
        lineStyle: { color: COLORS.compared, width: 2 },
        areaStyle: { color: hexRgba(COLORS.compared, 0.14) },
        itemStyle: { color: COLORS.compared }
      });
    }
    return {
      backgroundColor: 'transparent',
      animation: false,
      title: { text: group.name, left: 'center', top: 6, textStyle: { color: '#222', fontSize: 14, fontWeight: 600 } },
      legend: { bottom: 2, textStyle: { color: '#444', fontSize: 11 }, itemWidth: 16, itemHeight: 8 },
      tooltip: { trigger: 'item', confine: true },
      radar: {
        indicator: indicator, center: ['50%', '55%'], radius: '62%', splitNumber: 4,
        axisName: { color: '#333', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.12)' } },
        splitArea: { areaStyle: { color: ['rgba(0,0,0,0.015)', 'rgba(0,0,0,0.04)'] } },
        axisLine: { lineStyle: { color: 'rgba(0,0,0,0.12)' } }
      },
      series: [{ type: 'radar', data: data }]
    };
  }

  /**
   * Dibuja los 3 radar charts de percentiles del jugador.
   * @param {Object} player Objeto del jugador (player.json)
   * @param {Object} comparison player_stats_comparison.json
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {Object} { charts, state } o null si no hay datos
   */
  function renderPlayerRadarCharts(player, comparison, el, opts) {
    var ec = resolveEcharts(opts);
    comparison = comparison || {};

    // Posición del jugador y percentiles de esa posición.
    var pos = findPosition(player, comparison);
    if (!pos) { el.innerHTML = '<div style="font:14px system-ui;color:#a00;">No comparison data for this player.</div>'; return null; }
    var percentiles = comparison[pos].Percentiles;
    var groups = GROUPINGS[pos];
    if (!groups) { el.innerHTML = '<div style="font:14px system-ui;color:#a00;">No radar layout for position ' + pos + '.</div>'; return null; }

    // Estado compartido por los 3 radares.
    var state = {
      player: percentiles[player.ID],
      playerName: (percentiles[player.ID] && percentiles[player.ID].Name) || player.Name || 'Player',
      similar: similarMean(player, percentiles, groups),
      showSimilar: false,
      compared: null,
      comparedName: ''
    };

    // Construye el DOM e instancia los 3 radares.
    var list = samePositionPlayers(percentiles, player.ID);
    var dom = buildDom(el, list, opts);
    var charts = dom.chartDoms.map(function (d) { return ec.getInstanceByDom(d) || ec.init(d); });

    // Redibuja los 3 radares con el estado actual.
    function update() {
      charts.forEach(function (c, i) { c.setOption(radarOption(groups[i], state), true); });
    }
    update();

    // Toggle de la media de similares.
    dom.simCb.addEventListener('change', function () { state.showSimilar = dom.simCb.checked; update(); });

    // Buscador: compara con el jugador elegido (por nombre).
    var nameToId = {};
    list.forEach(function (p) { nameToId[p.name.toLowerCase()] = p.id; });
    dom.input.addEventListener('change', function () {
      var id = nameToId[(dom.input.value || '').trim().toLowerCase()];
      if (id && percentiles[id]) { state.compared = percentiles[id]; state.comparedName = percentiles[id].Name || id; }
      else { state.compared = null; state.comparedName = ''; }
      update();
    });
    dom.clearBtn.addEventListener('click', function () { dom.input.value = ''; state.compared = null; state.comparedName = ''; update(); });

    // Reajuste al redimensionar.
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(function () { charts.forEach(function (c) { c.resize(); }); });
      ro.observe(el);
    } else if (typeof global.addEventListener === 'function') {
      global.addEventListener('resize', function () { charts.forEach(function (c) { c.resize(); }); });
    }

    return { charts: charts, state: state };
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderPlayerRadarCharts = renderPlayerRadarCharts;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderPlayerRadarCharts;
  }
})(typeof window !== 'undefined' ? window : this);
