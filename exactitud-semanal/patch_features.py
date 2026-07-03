#!/usr/bin/env python3
"""Aplica las 4 nuevas funcionalidades al dashboard HTML."""
import re

HTML = "reporte_quiebres_actualizado.html"

with open(HTML, "r", encoding="utf-8") as f:
    html = f.read()

# ══════════════════════════════════════════════════════════════════════
# 1. NAV — botón "Evolución" + selector planta + buscador SKU
# ══════════════════════════════════════════════════════════════════════
html = html.replace(
    '<button class="tipo-btn" id="vbtn-riesgos" onclick="setVista(\'riesgos\',this)">⚠ Riesgos</button>',
    '<button class="tipo-btn" id="vbtn-riesgos" onclick="setVista(\'riesgos\',this)">⚠ Riesgos</button>\n'
    '      <button class="tipo-btn" id="vbtn-evolucion" onclick="setVista(\'evolucion\',this)">📈 Evolución</button>',
    1
)

# Agregar filtros después del select de semana
html = html.replace(
    '    </select>\n  </div>\n</nav>',
    '''    </select>
    <select class="week-sel tipo-toggle" id="plantaSel" onchange="setPlanta(this.value)"
            style="min-width:130px;font-size:11px" title="Filtrar por planta">
      <option value="all">Todas las plantas</option>
    </select>
    <input type="text" id="skuSearchInput" class="week-sel"
           placeholder="🔍 Buscar SKU…" oninput="setSkuSearch(this.value)"
           style="min-width:140px;font-size:11px;cursor:text"
           title="Filtrar por nombre de SKU">
  </div>
</nav>''',
    1
)

# ══════════════════════════════════════════════════════════════════════
# 2. BODY — nueva sección Evolución (antes del footer)
# ══════════════════════════════════════════════════════════════════════
SEC_EVOLUCION = '''
<!-- ⑦ EVOLUCIÓN -->
<div id="sec-evolucion" style="display:none">
<section>
  <div class="section-label" style="color:#1A5276">📈 Evolución Semanal · Quiebres y Bloqueos</div>
  <div class="panel" style="margin-bottom:14px">
    <div class="panel-title">Toneladas por Semana <em id="evoSubtitle">S01–S27 · Todos</em></div>
    <canvas id="evoCanvas" style="width:100%;height:320px;display:block"></canvas>
    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:10px;font-size:11px;color:var(--muted)">
      <span style="display:flex;align-items:center;gap:5px"><span style="width:18px;height:3px;background:#C8001E;display:inline-block"></span>Quebrados</span>
      <span style="display:flex;align-items:center;gap:5px"><span style="width:18px;height:3px;background:#4A5568;display:inline-block"></span>Bloqueados</span>
      <span style="display:flex;align-items:center;gap:5px"><span style="width:18px;height:3px;background:#1A5276;display:inline-block;opacity:.6"></span>Combinado</span>
    </div>
  </div>
  <div class="g2">
    <div class="panel">
      <div class="panel-title">Resumen Anual <em>S01–S27</em></div>
      <div id="evoStats"></div>
    </div>
    <div class="panel">
      <div class="panel-title">Semanas destacadas</div>
      <div id="evoHighlights"></div>
    </div>
  </div>
</section>
</div>

<!-- Nuevos críticos: panel dentro de riesgos -->
'''

html = html.replace(
    '<footer style="text-align:center;',
    SEC_EVOLUCION + '<footer style="text-align:center;',
    1
)

# Panel de nuevos críticos dentro de sec-riesgos (antes de plantaTabs)
html = html.replace(
    '    <div class="panel" style="margin-bottom:14px">\n    <div class="panel-title">🏭 Desglose por Planta',
    '  <div class="panel" style="margin-bottom:14px;border-left:4px solid #C8001E" id="panel-nuevos-criticos">\n'
    '    <div class="panel-title" style="color:#8B1A1A">🔺 Nuevos Críticos esta Semana <em id="ncSub"></em></div>\n'
    '    <div id="nuevosCriticosBody"></div>\n'
    '  </div>\n'
    '    <div class="panel" style="margin-bottom:14px">\n    <div class="panel-title">🏭 Desglose por Planta',
    1
)

# ══════════════════════════════════════════════════════════════════════
# 3. JS — estado: currentPlanta, skuSearch
# ══════════════════════════════════════════════════════════════════════
html = html.replace(
    "let currentVista = 'quiebres';\nlet currentTipo  = 'all';\nlet currentSem   = 'all';",
    "let currentVista = 'quiebres';\nlet currentTipo  = 'all';\nlet currentSem   = 'all';\n"
    "let currentPlanta = 'all';\nlet skuSearch = '';",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 4. JS — setVista: manejar 'evolucion'
# ══════════════════════════════════════════════════════════════════════
# Añadir manejo de sec-evolucion en setVista
html = html.replace(
    "  const isRiesgos = vista === 'riesgos';\n"
    "  const secRiesgos = document.getElementById('sec-riesgos');\n"
    "  if(secRiesgos) secRiesgos.style.display = isRiesgos ? '' : 'none';\n"
    "  // ocultar/mostrar secciones principales\n"
    "  document.querySelectorAll('section.sec-main').forEach(el => {\n"
    "    el.style.display = isRiesgos ? 'none' : '';\n"
    "  });\n"
    "\n"
    "  // ocultar toggles de categoria/semana y cpfr en riesgos\n"
    "  document.querySelectorAll('.tipo-toggle:not(.vista-toggle), .week-sel, .cpfr-sel').forEach(el => {\n"
    "    el.style.display = isRiesgos ? 'none' : '';\n"
    "  });\n",
    "  const isRiesgos  = vista === 'riesgos';\n"
    "  const isEvolucion = vista === 'evolucion';\n"
    "  const secRiesgos  = document.getElementById('sec-riesgos');\n"
    "  const secEvol     = document.getElementById('sec-evolucion');\n"
    "  if(secRiesgos) secRiesgos.style.display = isRiesgos ? '' : 'none';\n"
    "  if(secEvol)    secEvol.style.display    = isEvolucion ? '' : 'none';\n"
    "  document.querySelectorAll('section.sec-main').forEach(el => {\n"
    "    el.style.display = (isRiesgos || isEvolucion) ? 'none' : '';\n"
    "  });\n"
    "\n"
    "  // ocultar toggles de semana/planta/búsqueda en riesgos y evolución\n"
    "  document.querySelectorAll('.week-sel, .cpfr-sel').forEach(el => {\n"
    "    el.style.display = isRiesgos ? 'none' : '';\n"
    "  });\n"
    "  document.querySelectorAll('.tipo-toggle:not(.vista-toggle)').forEach(el => {\n"
    "    el.style.display = isRiesgos ? 'none' : '';\n"
    "  });\n",
    1
)

# En setVista, agregar highlight del botón evolución y llamada renderEvolucion
html = html.replace(
    "  ['quiebres','bloqueos','combinado'].forEach(v => {\n"
    "    const b = document.getElementById('vbtn-' + v);\n"
    "    b.classList.toggle('active', v === vista);\n"
    "    b.style.color = v === vista ? '' : 'rgba(255,255,255,.5)';\n"
    "  });",
    "  ['quiebres','bloqueos','combinado','riesgos','evolucion'].forEach(v => {\n"
    "    const b = document.getElementById('vbtn-' + v);\n"
    "    if(!b) return;\n"
    "    b.classList.toggle('active', v === vista);\n"
    "    b.style.color = v === vista ? '' : 'rgba(255,255,255,.5)';\n"
    "  });",
    1
)

# Llamar renderEvolucion cuando corresponda
html = html.replace(
    "  if (!isRiesgos) renderAll();\n}",
    "  if (!isRiesgos && !isEvolucion) renderAll();\n"
    "  if (isEvolucion) renderEvolucion();\n}",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 5. JS — renderSKUs: filtro por planta + búsqueda
# ══════════════════════════════════════════════════════════════════════
html = html.replace(
    "  const skus = d.skus;\n  if (!skus.length) {",
    "  const q = skuSearch.trim().toLowerCase();\n"
    "  const skus = d.skus.filter(s =>\n"
    "    (currentPlanta === 'all' || s.pl === currentPlanta) &&\n"
    "    (!q || s.n.toLowerCase().includes(q))\n"
    "  );\n"
    "  if (!skus.length) {",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 6. JS — nuevas funciones: setPlanta, setSkuSearch, initPlantaSelect,
#          renderEvolucion, renderNuevosCriticos
# ══════════════════════════════════════════════════════════════════════
NEW_FUNCS = r"""
// ── PLANTA + BÚSQUEDA ─────────────────────────────────────────────────────────
function initPlantaSelect() {
  const sel = document.getElementById('plantaSel');
  if (!sel || sel.options.length > 1) return;
  // plantas desde los datos de quiebres globales
  const plantas = (DB_QUIEBRES.all.all.plantas || []).map(p => p.n).filter(Boolean);
  plantas.forEach(p => {
    const o = document.createElement('option');
    o.value = p; o.textContent = p;
    sel.appendChild(o);
  });
}
function setPlanta(val) {
  currentPlanta = val;
  renderAll();
}
function setSkuSearch(val) {
  skuSearch = val;
  renderAll();
}

// ── EVOLUCIÓN ─────────────────────────────────────────────────────────────────
function renderEvolucion() {
  const tipo = currentTipo;
  const semsQ = SEMS_Q[tipo] || SEMS_Q['all'];
  const semsB = SEMS_B[tipo] || SEMS_B['all'];
  const semsC = SEMS_C[tipo] || SEMS_C['all'];

  const sub = document.getElementById('evoSubtitle');
  if (sub) sub.textContent = `S01–${semsQ[semsQ.length-1]?.s||''} · ${tipo==='all'?'Todos':tipo}`;

  // ── Estadísticas ────────────────────────────────────────────────────────────
  const totalQ = semsQ.reduce((a,s) => a + s.q, 0);
  const maxQ   = Math.max(...semsQ.map(s => s.q));
  const minQ   = Math.min(...semsQ.filter(s=>s.q>0).map(s => s.q));
  const avgQ   = totalQ / semsQ.length;
  const peakW  = semsQ.find(s => s.q === maxQ);
  const currW  = semsQ[semsQ.length - 1];
  const prevW  = semsQ[semsQ.length - 2];
  const delta  = currW && prevW ? currW.q - prevW.q : 0;
  const fmtN   = n => n.toLocaleString('es-CL', {minimumFractionDigits:1, maximumFractionDigits:1});

  const statsEl = document.getElementById('evoStats');
  if (statsEl) statsEl.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px">
      ${[
        ['📦 Total YTD',       fmtN(totalQ) + ' ton', ''],
        ['📊 Promedio semanal', fmtN(avgQ)   + ' ton', ''],
        ['⬆ Máximo semana',    fmtN(maxQ)   + ' ton', peakW ? '(' + peakW.s + ')' : ''],
        ['⬇ Mínimo semana',    fmtN(minQ)   + ' ton', ''],
        ['⟳ Vs semana anterior', (delta >= 0 ? '▲ +' : '▼ ') + fmtN(Math.abs(delta)) + ' ton',
          currW ? currW.s : ''],
      ].map(([lbl,val,note]) => `
        <div style="display:flex;justify-content:space-between;align-items:baseline;
                    padding:7px 0;border-bottom:1px solid var(--border)">
          <span style="font-size:11px;color:var(--muted);font-weight:600">${lbl}</span>
          <span style="font-family:var(--cond);font-size:16px;font-weight:800;
                       color:${lbl.includes('Vs')?(delta>=0?'#C8001E':'#1a8a3a'):'var(--dark2)'}">${val}
            ${note ? `<span style="font-size:10px;color:var(--muted);font-weight:400"> ${note}</span>` : ''}
          </span>
        </div>`).join('')}
    </div>`;

  // Semanas destacadas
  const sorted = [...semsQ].sort((a,b) => b.q - a.q);
  const hilEl = document.getElementById('evoHighlights');
  if (hilEl) hilEl.innerHTML = `
    <div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:8px">Top 5 semanas con más quiebres</div>
    ${sorted.slice(0,5).map((s,i) => {
      const col = i===0?'#C8001E':i===1?'#c84000':i===2?'#b06010':'#4A5568';
      const pct = (s.q/maxQ*100).toFixed(1);
      return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <div style="min-width:32px;font-family:var(--cond);font-size:16px;font-weight:800;color:${col}">${s.s}</div>
        <div style="flex:1;background:var(--gray2);border-radius:4px;height:8px">
          <div style="height:8px;border-radius:4px;width:${pct}%;background:${col}"></div></div>
        <div style="min-width:60px;text-align:right;font-family:var(--cond);font-size:14px;
                    font-weight:800;color:${col}">${fmtN(s.q)}</div>
        <div style="font-size:9px;color:var(--muted)">ton</div>
      </div>`;
    }).join('')}`;

  // ── Canvas line chart ───────────────────────────────────────────────────────
  const canvas = document.getElementById('evoCanvas');
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth || 800;
  const H = 320;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const pad = {l:52, r:20, t:20, b:36};
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;
  const n  = semsQ.length;

  const allVals = [...semsQ, ...semsB].map(s => s.q);
  const yMax = Math.max(...allVals) * 1.1 || 1;

  const xOf = i => pad.l + (i / (n - 1)) * cw;
  const yOf = v => pad.t + ch - (v / yMax) * ch;

  // fondo
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg') || '#f4f5f7';
  ctx.fillRect(0, 0, W, H);

  // grid horizontal
  ctx.strokeStyle = '#e2e5ef'; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (ch / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = '#6B7280'; ctx.font = '10px system-ui';
    ctx.textAlign = 'right';
    ctx.fillText(fmtN(yMax * (1 - i/4)), pad.l - 4, y + 3);
  }

  // líneas verticales semanas
  ctx.strokeStyle = '#e2e5ef'; ctx.lineWidth = 0.3;
  semsQ.forEach((s, i) => {
    if (i % 4 === 0 || i === n - 1) {
      const x = xOf(i);
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, pad.t + ch); ctx.stroke();
      ctx.fillStyle = '#6B7280'; ctx.font = '9px system-ui'; ctx.textAlign = 'center';
      ctx.fillText(s.s, x, pad.t + ch + 14);
    }
  });

  // función para dibujar línea
  const drawLine = (sems, color, lineW, fill) => {
    if (!sems.length) return;
    ctx.beginPath();
    sems.forEach((s, i) => {
      const x = xOf(i), y = yOf(s.q);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    if (fill) {
      ctx.lineTo(xOf(n-1), pad.t + ch);
      ctx.lineTo(pad.l, pad.t + ch);
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.beginPath();
      sems.forEach((s, i) => {
        const x = xOf(i), y = yOf(s.q);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
    }
    ctx.strokeStyle = color; ctx.lineWidth = lineW;
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.stroke();
  };

  // área relleno quebrados
  drawLine(semsQ, '#C8001E', 2.5, 'rgba(200,0,30,.07)');
  // bloqueados
  drawLine(semsB, '#4A5568', 1.5, null);
  // combinado
  drawLine(semsC, '#1A5276', 1, null);

  // promedio móvil 3 semanas (quiebres)
  const ma3 = semsQ.map((s,i) => {
    const sl = semsQ.slice(Math.max(0, i-2), i+1);
    return {s:s.s, q: sl.reduce((a,x)=>a+x.q,0)/sl.length};
  });
  ctx.setLineDash([4,3]);
  drawLine(ma3, '#C8001E', 1.2, null);
  ctx.setLineDash([]);

  // puntos semana actual
  const lastI = n - 1;
  [[semsQ, '#C8001E'], [semsB, '#4A5568']].forEach(([sems, col]) => {
    const s = sems[lastI];
    ctx.beginPath();
    ctx.arc(xOf(lastI), yOf(s.q), 5, 0, Math.PI*2);
    ctx.fillStyle = col; ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    // etiqueta
    ctx.fillStyle = col; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'left';
    ctx.fillText(fmtN(s.q)+'t', xOf(lastI) + 7, yOf(s.q) + 4);
  });

  // punto máximo
  const maxI = semsQ.indexOf(peakW);
  if (maxI >= 0) {
    ctx.beginPath();
    ctx.arc(xOf(maxI), yOf(peakW.q), 4, 0, Math.PI*2);
    ctx.fillStyle = '#C8001E'; ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
  }
}

// ── NUEVOS CRÍTICOS ────────────────────────────────────────────────────────────
function renderNuevosCriticos() {
  const el = document.getElementById('nuevosCriticosBody');
  const sub = document.getElementById('ncSub');
  if (!el) return;
  const data = (typeof NUEVOS_CRITICOS !== 'undefined') ? NUEVOS_CRITICOS : [];
  if (sub) sub.textContent = data.length + ' SKUs';
  if (!data.length) {
    el.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--muted)">Sin nuevos críticos detectados esta semana ✅</div>';
    return;
  }
  const fmtN = n => n.toLocaleString('es-CL', {minimumFractionDigits:1,maximumFractionDigits:1});
  el.innerHTML = `
    <div style="overflow-x:auto">
    <table class="tbl" style="min-width:600px">
      <thead><tr>
        <th>#</th><th>SKU</th><th>Planta</th><th>Tipo</th>
        <th class="r">Ton S26</th><th class="r">Ton S27</th><th class="r">Δ</th>
      </tr></thead>
      <tbody>${data.map((r,i) => {
        const isNew = r.q26 === 0;
        const col = '#C8001E';
        return `<tr>
          <td style="font-family:var(--cond);font-size:14px;font-weight:800;color:var(--muted2)">${i+1}</td>
          <td style="font-weight:700;max-width:220px">
            <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${r.n}">${r.n}</div>
            ${isNew ? '<span style="font-size:9px;font-weight:800;color:#fff;background:#C8001E;padding:1px 6px;border-radius:10px;margin-top:2px;display:inline-block">NUEVO</span>' : ''}
          </td>
          <td style="font-size:11px;color:var(--muted)">${r.pl}</td>
          <td style="font-size:11px;color:var(--muted)">${r.tipo}</td>
          <td class="r"><div style="font-family:var(--cond);font-size:16px;color:var(--muted2)">${fmtN(r.q26)}</div><div class="tbl-unit">ton</div></td>
          <td class="r"><div style="font-family:var(--cond);font-size:16px;color:${col};font-weight:800">${fmtN(r.q27)}</div><div class="tbl-unit">ton</div></td>
          <td class="r"><div style="font-family:var(--cond);font-size:16px;font-weight:800;color:${col}">▲ ${fmtN(r.delta)}</div></td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>`;
}

"""

# Insertar nuevas funciones antes de "let riesgosFilter"
html = html.replace(
    "\nlet riesgosFilter='all';",
    NEW_FUNCS + "\nlet riesgosFilter='all';",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 7. JS — renderRiesgos: incluir nuevos críticos
# ══════════════════════════════════════════════════════════════════════
html = html.replace(
    "function renderRiesgos(){renderCharts();renderRiesgosTable();renderPlantaTabs();renderPlantaContent();}",
    "function renderRiesgos(){renderCharts();renderNuevosCriticos();renderRiesgosTable();renderPlantaTabs();renderPlantaContent();}",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 8. JS — init: poblar select de plantas + renderEvolucion al inicio
# ══════════════════════════════════════════════════════════════════════
html = html.replace(
    "renderAll();\nrenderRiesgos();",
    "initPlantaSelect();\nrenderAll();\nrenderRiesgos();",
    1
)

# ══════════════════════════════════════════════════════════════════════
# 9. Placeholder JS constante NUEVOS_CRITICOS (si no existe)
# ══════════════════════════════════════════════════════════════════════
if "const NUEVOS_CRITICOS=" not in html:
    html = html.replace(
        "const MERMAS_META=",
        "const NUEVOS_CRITICOS=[];\nconst MERMAS_META=",
        1
    )

with open(HTML, "w", encoding="utf-8") as f:
    f.write(html)

size = len(html.encode("utf-8")) / 1_048_576
print(f"✓ HTML actualizado ({size:.2f} MB)")
