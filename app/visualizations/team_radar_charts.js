/**
 * CREACIÓN DE 5 RADAR CHARTS DE PERCENTILES DE EQUIPO CON Apache ECharts
 */
(function (global) {
  'use strict';

  // Colores de cada serie (equipo, media de similares, equipo comparado).
  var COLORS = { team: '#154284', similar: '#EDBB00', compared: '#9d1009' };

  // Convierte un color hex (#rgb o #rrggbb) a rgba con la opacidad indicada.
  function hexRgba(hex, a) {
    var h = String(hex).replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  // Grupos de métricas -> 5 radares. Orden: arriba Attack/Creation/Possession, abajo Goalkeeping/Defending.
  var GROUPS = [
    { name: 'Attack', metrics: ['GoalsPer90', 'ExpectedGoalsPer90', 'TotalShotsPer90', 'ShotsOnTargetPer90', 'ShotAccuracy', 'GoalConversion', 'BigChanceConversion', 'TouchesInOppBoxPer90'] },
    { name: 'Creation', metrics: ['KeyPassesPer90', 'ExpectedAssistsPer90', 'BigChancesCreatedPer90', 'FinalThirdEntriesPer90', 'CrossesPer90', 'CrossAccuracy', 'ProgressiveFieldTilt', 'FinalThirdEfficiency'] },
    { name: 'Possession', metrics: ['BallPossession', 'PassAccuracy', 'PassesPer90', 'OppositionHalfPassAccuracy', 'OppositionHalfPassShare', 'LongBallAccuracy', 'BallPossessionPerPass', 'PossessionLossRate'] },
    { name: 'Goalkeeping', metrics: ['SaveRate', 'SavedShotsInsideBoxRate', 'GoalsPreventedPer90', 'CleanSheets', 'HighClaimRate', 'KeeperSweeperAccuracy', 'PenaltySaveRate', 'GoalsConcededPer90'] },
    { name: 'Defending', metrics: ['TacklesPer90', 'InterceptionsPer90', 'BallRecoveriesPer90', 'ClearancesPer90', 'DuelWinRate', 'AerialWinRate', 'DefensiveActionSuccess', 'ChallengesLostRate'] }
  ];

  // Etiquetas cortas de los ejes (fallback: humanizar el nombre).
  var LABELS = {
    GoalsPer90: 'Goals/90', ExpectedGoalsPer90: 'xG/90', TotalShotsPer90: 'Shots/90', ShotsOnTargetPer90: 'SoT/90',
    ShotAccuracy: 'Shot Acc.', GoalConversion: 'Goal Conv.', BigChanceConversion: 'Big Ch. Conv.', TouchesInOppBoxPer90: 'Box Touches/90',
    KeyPassesPer90: 'Key Passes/90', ExpectedAssistsPer90: 'xA/90', BigChancesCreatedPer90: 'Big Chances/90', FinalThirdEntriesPer90: 'Final 3rd/90',
    CrossesPer90: 'Crosses/90', CrossAccuracy: 'Cross %', ProgressiveFieldTilt: 'Field Tilt', FinalThirdEfficiency: 'Final 3rd Eff.',
    BallPossession: 'Possession %', PassAccuracy: 'Pass %', PassesPer90: 'Passes/90', OppositionHalfPassAccuracy: 'Opp½ Pass %',
    OppositionHalfPassShare: 'Opp½ Share', LongBallAccuracy: 'Long Ball %', BallPossessionPerPass: 'Poss./Pass', PossessionLossRate: 'Poss. Keep',
    TacklesPer90: 'Tackles/90', InterceptionsPer90: 'Intercept./90', BallRecoveriesPer90: 'Recoveries/90', ClearancesPer90: 'Clearances/90',
    DuelWinRate: 'Duel %', AerialWinRate: 'Aerial %', DefensiveActionSuccess: 'Def Success', ChallengesLostRate: 'Challenges Kept',
    SaveRate: 'Save %', SavedShotsInsideBoxRate: 'Box Save %', GoalsPreventedPer90: 'Goals Prev./90', CleanSheets: 'Clean Sheets',
    HighClaimRate: 'High Claim %', KeeperSweeperAccuracy: 'Sweeper %', PenaltySaveRate: 'Pen Save %', GoalsConcededPer90: 'Solidity'
  };

  // Devuelve la instancia de ECharts (de opts o global) o lanza error si no existe.
  function resolveEcharts(opts) {
    var ec = (opts && opts.echarts) || global.echarts;
    if (!ec) throw new Error('[team_radar_charts] ECharts no está disponible.');
    return ec;
  }

  // Comprueba que un valor sea un número finito.
  function isNum(v) { return typeof v === 'number' && isFinite(v); }

  // Etiqueta legible de una métrica.
  function labelOf(m) { return LABELS[m] || m.replace(/Per90/, '/90').replace(/([a-z])([A-Z])/g, '$1 $2'); }

  // Valor de percentil de una métrica (0 si falta).
  function pv(obj, m) { return obj && isNum(obj[m]) ? obj[m] : 0; }

  // Media de percentiles de los SimilarTeams presentes.
  function similarMean(team, percentiles) {
    var sims = (team && team.SimilarTeams) || [];
    var rows = [];
    sims.forEach(function (s) { var pc = percentiles[s.Team]; if (pc) rows.push(pc); });
    if (!rows.length) return null;
    // Métricas únicas de los grupos.
    var metrics = {};
    GROUPS.forEach(function (g) { g.metrics.forEach(function (m) { metrics[m] = true; }); });
    var out = {};
    Object.keys(metrics).forEach(function (m) {
      var sum = 0, c = 0;
      rows.forEach(function (r) { if (isNum(r[m])) { sum += r[m]; c++; } });
      out[m] = c ? sum / c : 0;
    });
    return out;
  }

  // Lista {id, name} de todos los equipos (para el buscador).
  function allTeams(percentiles, excludeId) {
    return Object.keys(percentiles)
      .filter(function (id) { return id !== excludeId; })
      .map(function (id) { return { id: id, name: percentiles[id].Name || id }; })
      .sort(function (a, b) { return a.name.localeCompare(b.name); });
  }

  // Crea el DOM (controles + 5 contenedores de radar).
  function buildDom(el, teams) {
    el.innerHTML = '';
    var controls = document.createElement('div');
    controls.style.cssText = 'display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;margin:0 0 8px;font:13px system-ui,sans-serif;color:#222;';
    // Checkbox de similares.
    var simLabel = document.createElement('label');
    simLabel.style.cssText = 'display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;';
    var simCb = document.createElement('input');
    simCb.type = 'checkbox';
    simLabel.appendChild(simCb);
    simLabel.appendChild(document.createTextNode('Show mean percentiles of similar teams'));
    // Buscador de equipo.
    var searchWrap = document.createElement('div');
    searchWrap.style.cssText = 'display:flex;align-items:center;gap:6px;';
    var input = document.createElement('input');
    input.setAttribute('list', 'radar-teams-' + Math.random().toString(36).slice(2));
    input.placeholder = 'Compare with team…';
    input.style.cssText = 'padding:5px 8px;border:1px solid #ccc;border-radius:4px;min-width:220px;font:13px system-ui,sans-serif;';
    var datalist = document.createElement('datalist');
    datalist.id = input.getAttribute('list');
    teams.forEach(function (t) { var o = document.createElement('option'); o.value = t.name; datalist.appendChild(o); });
    var clearBtn = document.createElement('button');
    clearBtn.textContent = 'Clear';
    clearBtn.style.cssText = 'padding:5px 10px;border:1px solid #ccc;border-radius:4px;background:#f3f3f3;cursor:pointer;';
    searchWrap.appendChild(input); searchWrap.appendChild(datalist); searchWrap.appendChild(clearBtn);
    controls.appendChild(simLabel); controls.appendChild(searchWrap);
    el.appendChild(controls);
    // Dos filas: arriba 3 radares, abajo 2 (centrados).
    var charts = [];
    function mkRow() { var r = document.createElement('div'); r.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;justify-content:center;'; return r; }
    var topRow = mkRow(), bottomRow = mkRow();
    var i;
    for (i = 0; i < 3; i++) { var d = document.createElement('div'); d.style.cssText = 'flex:1 1 300px;min-width:260px;height:330px;'; topRow.appendChild(d); charts.push(d); }
    for (i = 0; i < 2; i++) { var d2 = document.createElement('div'); d2.style.cssText = 'flex:0 1 360px;min-width:280px;height:330px;'; bottomRow.appendChild(d2); charts.push(d2); }
    el.appendChild(topRow);
    el.appendChild(bottomRow);
    return { simCb: simCb, input: input, clearBtn: clearBtn, chartDoms: charts };
  }

  // Construye la option de un radar (un grupo) según el estado.
  function radarOption(group, state) {
    var indicator = group.metrics.map(function (m) { return { name: labelOf(m), max: 100 }; });
    var data = [];
    data.push({
      value: group.metrics.map(function (m) { return Math.round(pv(state.team, m)); }),
      name: state.teamName,
      lineStyle: { color: COLORS.team, width: 2 }, areaStyle: { color: hexRgba(COLORS.team, 0.18) }, itemStyle: { color: COLORS.team }
    });
    if (state.showSimilar && state.similar) {
      data.push({
        value: group.metrics.map(function (m) { return Math.round(pv(state.similar, m)); }),
        name: 'Similar teams (avg)',
        lineStyle: { color: COLORS.similar, width: 2, type: 'dashed' }, areaStyle: { color: hexRgba(COLORS.similar, 0.12) }, itemStyle: { color: COLORS.similar }
      });
    }
    if (state.compared) {
      data.push({
        value: group.metrics.map(function (m) { return Math.round(pv(state.compared, m)); }),
        name: state.comparedName,
        lineStyle: { color: COLORS.compared, width: 2 }, areaStyle: { color: hexRgba(COLORS.compared, 0.14) }, itemStyle: { color: COLORS.compared }
      });
    }
    return {
      backgroundColor: 'transparent', animation: false,
      title: { text: group.name, left: 'center', top: 6, textStyle: { color: '#222', fontSize: 14, fontWeight: 600 } },
      legend: { bottom: 2, textStyle: { color: '#444', fontSize: 11 }, itemWidth: 16, itemHeight: 8 },
      tooltip: { trigger: 'item', confine: true },
      radar: {
        indicator: indicator, center: ['50%', '54%'], radius: '60%', splitNumber: 4,
        axisName: { color: '#333', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.12)' } },
        splitArea: { areaStyle: { color: ['rgba(0,0,0,0.015)', 'rgba(0,0,0,0.04)'] } },
        axisLine: { lineStyle: { color: 'rgba(0,0,0,0.12)' } }
      },
      series: [{ type: 'radar', data: data }]
    };
  }

  /**
   * Dibuja los 5 radar charts de percentiles del equipo.
   * @param {Object} team Objeto del equipo (team.json) con .ID y .SimilarTeams
   * @param {Object} comparison team_stats_comparison.json
   * @param {HTMLElement} el Contenedor
   * @param {Object} [opts] Opciones
   * @returns {Object} { charts, state } o null si no hay datos
   */
  function renderTeamRadarCharts(team, comparison, el, opts) {
    var ec = resolveEcharts(opts);
    var percentiles = (comparison && comparison.Percentiles) || {};
    if (!team || !percentiles[team.ID]) { el.innerHTML = '<div style="font:14px system-ui;color:#a00;">No comparison data for this team.</div>'; return null; }

    // Estado compartido por los 5 radares.
    var state = {
      team: percentiles[team.ID],
      teamName: (percentiles[team.ID] && percentiles[team.ID].Name) || team.Name || 'Team',
      similar: similarMean(team, percentiles),
      showSimilar: false,
      compared: null,
      comparedName: ''
    };

    // DOM e instancias.
    var list = allTeams(percentiles, team.ID);
    var dom = buildDom(el, list);
    var charts = dom.chartDoms.map(function (d) { return ec.getInstanceByDom(d) || ec.init(d); });

    // Redibuja los 5 radares con el estado actual.
    function update() { charts.forEach(function (c, i) { c.setOption(radarOption(GROUPS[i], state), true); }); }
    update();

    // Toggle de la media de similares.
    dom.simCb.addEventListener('change', function () { state.showSimilar = dom.simCb.checked; update(); });

    // Buscador: compara con el equipo elegido (por nombre).
    var nameToId = {};
    list.forEach(function (t) { nameToId[t.name.toLowerCase()] = t.id; });
    dom.input.addEventListener('change', function () {
      var id = nameToId[(dom.input.value || '').trim().toLowerCase()];
      if (id && percentiles[id]) { state.compared = percentiles[id]; state.comparedName = percentiles[id].Name || id; }
      else { state.compared = null; state.comparedName = ''; }
      update();
    });
    dom.clearBtn.addEventListener('click', function () { dom.input.value = ''; state.compared = null; state.comparedName = ''; update(); });

    // Reajuste al redimensionar.
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(function () { charts.forEach(function (c) { c.resize(); }); }); ro.observe(el);
    } else if (typeof global.addEventListener === 'function') {
      global.addEventListener('resize', function () { charts.forEach(function (c) { c.resize(); }); });
    }

    return { charts: charts, state: state };
  }

  // Exporta la función al ámbito global y como módulo si procede.
  global.renderTeamRadarCharts = renderTeamRadarCharts;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = renderTeamRadarCharts;
  }
})(typeof window !== 'undefined' ? window : this);
