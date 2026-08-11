/* ===== App State ===== */
const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? 'http://localhost:8000/api'
  : './data'; // fallback: load static JSON from web/data/

let allMunicipios = [];
let allRanking = [];
let currentWeights = { apertura: 30, compras: 30, rendicion: 20, declaraciones: 20 };

/* ===== Data Loading ===== */
async function loadData() {
  try {
    // Try API first
    const res = await fetch(`${API_BASE}/ranking?limit=200`);
    if (res.ok) {
      const data = await res.json();
      allRanking = data.ranking;
    } else {
      throw new Error('API not available');
    }
  } catch (e) {
    // Fallback to static JSON
    console.log('API no disponible, cargando datos estáticos...');
    try {
      const res = await fetch('./data/transparency_index.json');
      if (res.ok) {
        allRanking = await res.json();
      } else {
        allRanking = [];
      }
    } catch (e2) {
      allRanking = [];
    }
  }

  // Load stats
  if (allRanking.length > 0) {
    const indices = allRanking.map(m => m.indice_transparencia || 0);
    document.getElementById('statTotal').textContent = allRanking.length;
    document.getElementById('statAvg').textContent = (indices.reduce((a,b) => a+b, 0) / indices.length).toFixed(1);
    document.getElementById('statMax').textContent = Math.max(...indices).toFixed(1);
    document.getElementById('statMin').textContent = Math.min(...indices).toFixed(1);
  }

  // Populate selects
  populateSelects();

  // Render views
  renderRanking(allRanking);
  renderMap(allRanking);
}

function populateSelects() {
  // Province filter
  const provinces = [...new Set(allRanking.map(m => m.provincia).filter(Boolean))].sort();
  const provSelect = document.getElementById('filterProvince');
  provinces.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = p;
    provSelect.appendChild(opt);
  });

  // Comparator & contracts selects
  ['comparatorMuni', 'contractsMuni'].forEach(id => {
    const sel = document.getElementById(id);
    allRanking.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.municipio_id;
      opt.textContent = `${m.nombre} (${m.provincia || ''})`;
      sel.appendChild(opt);
    });
  });
}

/* ===== Navigation ===== */
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('view-active'));
    const viewId = link.dataset.view;
    document.getElementById(`view-${viewId}`).classList.add('view-active');
  });
});

/* ===== Weights Panel ===== */
function updateWeightsDisplay() {
  const sum = currentWeights.apertura + currentWeights.compras + currentWeights.rendicion + currentWeights.declaraciones;
  document.getElementById('wAperturaVal').textContent = currentWeights.apertura + '%';
  document.getElementById('wComprasVal').textContent = currentWeights.compras + '%';
  document.getElementById('wRendicionVal').textContent = currentWeights.rendicion + '%';
  document.getElementById('wDeclaracionesVal').textContent = currentWeights.declaraciones + '%';
  document.getElementById('weightsTotal').textContent = sum + '%';
  document.getElementById('weightsWarning').style.display = sum === 100 ? 'none' : 'inline';
}

['wApertura', 'wCompras', 'wRendicion', 'wDeclaraciones'].forEach(id => {
  const key = id.replace('w', '').toLowerCase();
  document.getElementById(id).addEventListener('input', (e) => {
    currentWeights[key] = parseInt(e.target.value);
    updateWeightsDisplay();
  });
});

document.getElementById('resetWeights').addEventListener('click', () => {
  currentWeights = { apertura: 30, compras: 30, rendicion: 20, declaraciones: 20 };
  document.getElementById('wApertura').value = 30;
  document.getElementById('wCompras').value = 30;
  document.getElementById('wRendicion').value = 20;
  document.getElementById('wDeclaraciones').value = 20;
  updateWeightsDisplay();
  renderRanking(allRanking);
});

// Recalculate on slider release
['wApertura', 'wCompras', 'wRendicion', 'wDeclaraciones'].forEach(id => {
  const key = id.replace('w', '').toLowerCase();
  document.getElementById(id).addEventListener('change', () => {
    recalculateIndex();
  });
});

function recalculateIndex() {
  const sum = currentWeights.apertura + currentWeights.compras + currentWeights.rendicion + currentWeights.declaraciones;
  if (sum !== 100) return;

  // Try API
  fetch(`${API_BASE}/weights`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      apertura: currentWeights.apertura / 100,
      compras: currentWeights.compras / 100,
      rendicion: currentWeights.rendicion / 100,
      declaraciones: currentWeights.declaraciones / 100,
    })
  }).then(r => r.json()).then(data => {
    if (data.ranking) {
      allRanking = data.ranking;
      renderRanking(allRanking);
      renderMap(allRanking);
    }
  }).catch(() => {
    // Client-side recalculation
    const w = {
      apertura: currentWeights.apertura / 100,
      compras: currentWeights.compras / 100,
      rendicion: currentWeights.rendicion / 100,
      declaraciones: currentWeights.declaraciones / 100,
    };
    allRanking.forEach(m => {
      m.indice_transparencia = Math.round(
        (m.sub_apertura_score || 0) * w.apertura +
        (m.sub_compras_score || 0) * w.compras +
        (m.sub_rendicion_score || 0) * w.rendicion +
        (m.sub_declaraciones_score || 0) * w.declaraciones
      , 1);
    });
    allRanking.sort((a, b) => b.indice_transparencia - a.indice_transparencia);
    allRanking.forEach((m, i) => m.ranking = i + 1);
    renderRanking(allRanking);
    renderMap(allRanking);
  });
}

/* ===== Ranking Table ===== */
function renderRanking(data) {
  const tbody = document.getElementById('rankingBody');
  tbody.innerHTML = '';
  data.forEach(m => {
    const idx = m.indice_transparencia || 0;
    const cls = idx >= 60 ? 'index-high' : idx >= 35 ? 'index-mid' : 'index-low';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${m.ranking || ''}</td>
      <td><strong>${m.nombre || ''}</strong></td>
      <td>${m.provincia || ''}</td>
      <td>${(m.poblacion || 0).toLocaleString('es-EC')}</td>
      <td><span class="index-badge ${cls}">${idx.toFixed(1)}</span></td>
      <td>${renderSubBar(m.sub_apertura_score)}</td>
      <td>${renderSubBar(m.sub_compras_score)}</td>
      <td>${renderSubBar(m.sub_rendicion_score)}</td>
      <td>${renderSubBar(m.sub_declaraciones_score)}</td>
      <td><button class="btn btn-primary" style="padding:.25rem .5rem;font-size:.75rem;" onclick="loadComparatorFor('${m.municipio_id}')">Comparar</button></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderSubBar(score) {
  const s = score || 0;
  const color = s >= 60 ? 'var(--green)' : s >= 35 ? 'var(--orange)' : 'var(--red)';
  return `<span class="subindex-bar"><span class="subindex-fill" style="width:${s}%;background:${color}"></span></span>${s.toFixed(0)}`;
}

// Filter handling
document.getElementById('applyFilters').addEventListener('click', () => {
  const prov = document.getElementById('filterProvince').value;
  const minPop = parseInt(document.getElementById('filterMinPop').value) || 0;
  const maxPop = parseInt(document.getElementById('filterMaxPop').value) || Infinity;

  let filtered = allRanking.filter(m => {
    if (prov && m.provincia !== prov) return false;
    if ((m.poblacion || 0) < minPop) return false;
    if ((m.poblacion || 0) > maxPop) return false;
    return true;
  });

  // Re-rank
  filtered.forEach((m, i) => m.ranking = i + 1);
  renderRanking(filtered);
});

// Sortable columns
document.querySelectorAll('.ranking-table th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const sortBy = th.dataset.sort;
    const currentOrder = th.textContent.includes('↓') ? 'asc' : 'desc';
    document.querySelectorAll('.ranking-table th').forEach(t => {
      t.textContent = t.textContent.replace(/[↑↓]/g, '').trim();
    });
    th.textContent += currentOrder === 'asc' ? ' ↑' : ' ↓';
    const sorted = [...allRanking].sort((a, b) => {
      const va = a[sortBy] || 0;
      const vb = b[sortBy] || 0;
      return currentOrder === 'asc' ? va - vb : vb - va;
    });
    sorted.forEach((m, i) => m.ranking = i + 1);
    renderRanking(sorted);
  });
});

/* ===== Map (SVG Choropleth Placeholder) ===== */
function renderMap(data) {
  const svg = d3.select('#mapSvg');
  svg.selectAll('* *').remove();

  if (data.length === 0) return;

  // Since we don't have the actual Ecuador topojson loaded,
  // create a grid-based visual representation
  const cols = 8;
  const rows = Math.ceil(data.length / cols);
  const cellW = 65;
  const cellH = 50;
  const padding = 5;

  const colorScale = d3.scaleSequential()
    .domain([0, 100])
    .interpolator(d3.interpolateRgbBasis(['#f87171', '#fb923c', '#facc15', '#4ade80']));

  data.forEach((m, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = col * (cellW + padding) + 20;
    const y = row * (cellH + padding) + 20;
    const idx = m.indice_transparencia || 0;

    const g = svg.append('g')
      .attr('transform', `translate(${x}, ${y})`)
      .style('cursor', 'pointer');

    g.append('rect')
      .attr('width', cellW)
      .attr('height', cellH)
      .attr('rx', 6)
      .attr('fill', colorScale(idx))
      .attr('stroke', '#334155')
      .attr('stroke-width', 1)
      .on('mouseover', (e) => {
        const tooltip = document.getElementById('mapTooltip');
        tooltip.style.display = 'block';
        tooltip.style.left = (e.offsetX + 10) + 'px';
        tooltip.style.top = (e.offsetY + 10) + 'px';
        tooltip.innerHTML = `<strong>${m.nombre}</strong><br>Índice: ${idx.toFixed(1)}<br>${m.provincia || ''}`;
      })
      .on('mouseout', () => {
        document.getElementById('mapTooltip').style.display = 'none';
      })
      .on('click', () => loadComparatorFor(m.municipio_id));

    g.append('text')
      .attr('x', cellW / 2)
      .attr('y', cellH / 2 - 5)
      .attr('text-anchor', 'middle')
      .attr('fill', '#0f172a')
      .style('font-size', '9px')
      .style('font-weight', '700')
      .text(m.nombre ? m.nombre.substring(0, 8) : '');

    g.append('text')
      .attr('x', cellW / 2)
      .attr('y', cellH / 2 + 10)
      .attr('text-anchor', 'middle')
      .attr('fill', '#0f172a')
      .style('font-size', '11px')
      .style('font-weight', '800')
      .text(idx.toFixed(0));
  });

  // Legend
  const legend = document.getElementById('mapLegend');
  legend.innerHTML = '<span>0</span><div class="gradient-bar"></div><span>100</span>';
}

/* ===== Comparator ===== */
function loadComparatorFor(municipioId) {
  // Switch to comparator view
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelector('[data-view="comparador"]').classList.add('active');
  document.querySelectorAll('.view').forEach(v => v.classList.remove('view-active'));
  document.getElementById('view-comparador').classList.add('view-active');

  document.getElementById('comparatorMuni').value = municipioId;
  loadComparator();
}

document.getElementById('loadComparator').addEventListener('click', loadComparator);

async function loadComparator() {
  const muniId = document.getElementById('comparatorMuni').value;
  if (!muniId) return;

  const container = document.getElementById('comparatorResults');
  container.innerHTML = '<p class="placeholder-text">Cargando...</p>';

  // Get similar municipios
  let similar = [];
  try {
    const res = await fetch(`${API_BASE}/municipio/${muniId}/similar`);
    if (res.ok) {
      const data = await res.json();
      similar = data.similares || [];
    } else { throw new Error(); }
  } catch (e) {
    // Fallback: load static similar data
    try {
      const res = await fetch('./data/similar_municipios.json');
      if (res.ok) {
        const allSimilar = await res.json();
        similar = allSimilar.filter(s => s.municipio_id_origen === muniId);
      }
    } catch (e2) { similar = []; }
  }

  // Get main municipio data
  const mainMuni = allRanking.find(m => m.municipio_id === muniId);
  if (!mainMuni) return;

  // Get similar municipios full data
  const similarFull = similar.map(s => {
    return allRanking.find(m => m.municipio_id === s.municipio_id_similar);
  }).filter(Boolean);

  if (similarFull.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No hay datos de municipios similares disponibles.</p>';
    return;
  }

  // Render small multiples
  const allMunis = [mainMuni, ...similarFull];
  let html = '<div class="comparator-group">';
  html += '<div class="comparator-group-title">Sparklines de compras (sintético · últimos 3 años)</div>';
  html += '<div class="small-multiples-grid">';

  allMunis.forEach((m, i) => {
    const isMain = i === 0;
    const idx = m.indice_transparencia || 0;
    const color = idx >= 60 ? 'var(--green)' : idx >= 35 ? 'var(--orange)' : 'var(--red)';
    html += `
      <div class="small-multiple" style="${isMain ? 'border:2px solid var(--primary);' : ''}">
        <h4>${m.nombre}${isMain ? ' ⭐' : ''}</h4>
        <div class="muni-index" style="color:${color}">${idx.toFixed(1)}</div>
        <canvas id="spark_${m.municipio_id}"></canvas>
        <div style="font-size:.75rem;color:var(--text-muted);margin-top:.25rem;">${m.provincia || ''} · Pop: ${(m.poblacion||0).toLocaleString('es-EC')}</div>
      </div>
    `;
  });
  html += '</div></div>';

  // Sub-index comparison bars
  html += '<div class="comparator-group">';
  html += '<div class="comparator-group-title">Comparación de subíndices</div>';
  html += '<div class="subindex-comparison">';

  const subindices = [
    { key: 'sub_apertura_score', label: 'Apertura de Datos', max: 100 },
    { key: 'sub_compras_score', label: 'Compras Públicas', max: 100 },
    { key: 'sub_rendicion_score', label: 'Rendición y Auditoría', max: 100 },
    { key: 'sub_declaraciones_score', label: 'Declaraciones Patrimoniales', max: 100 },
  ];

  subindices.forEach(si => {
    html += `<div class="subindex-comparison-card"><h4>${si.label}</h4><div class="sub-bars">`;
    allMunis.forEach((m, i) => {
      const val = m[si.key] || 0;
      const isMain = i === 0;
      const color = isMain ? 'var(--primary)' : val >= 60 ? 'var(--green)' : val >= 35 ? 'var(--orange)' : 'var(--red)';
      html += `
        <div class="sub-bar-row">
          <span class="sub-bar-label" style="${isMain ? 'color:var(--primary);font-weight:700;' : ''}">${m.nombre.substring(0,12)}</span>
          <span class="sub-bar-track"><span class="sub-bar-fill" style="width:${val}%;background:${color}"></span></span>
          <span class="sub-bar-value">${val.toFixed(0)}</span>
        </div>
      `;
    });
    html += '</div></div>';
  });
  html += '</div></div>';

  // Differences table
  html += '<div class="comparator-group">';
  html += '<div class="comparator-group-title">Diferencias con el municipio seleccionado</div>';
  html += '<table class="ranking-table"><thead><tr><th>Métrica</th>';
  similarFull.forEach(m => html += `<th>${m.nombre}</th>`);
  html += '</tr></thead><tbody>';

  const metrics = [
    { key: 'indice_transparencia', label: 'Índice de Transparencia' },
    { key: 'pct_licitacion_publica', label: '% Licitación Pública' },
    { key: 'pct_contratacion_directa', label: '% Contratación Directa' },
    { key: 'hhi_proveedores', label: 'HHI Proveedores' },
    { key: 'num_contratos', label: 'N° Contratos' },
    { key: 'monto_total_contratos', label: 'Monto Total (USD)' },
    { key: 'pct_declaraciones', label: '% Declaraciones' },
    { key: 'pct_informes_auditoria', label: '% Informes Auditoría' },
    { key: 'num_sanciones', label: 'N° Sanciones' },
  ];

  metrics.forEach(metric => {
    html += `<tr><td><strong>${metric.label}</strong></td>`;
    similarFull.forEach(m => {
      const mainVal = mainMuni[metric.key] || 0;
      const muniVal = m[metric.key] || 0;
      const diff = muniVal - mainVal;
      const cls = diff > 0 ? 'index-high' : diff < 0 ? 'index-low' : '';
      const sign = diff > 0 ? '+' : '';
      html += `<td>${muniVal.toLocaleString('es-EC')} <span class="index-badge ${cls}">${sign}${diff.toLocaleString('es-EC')}</span></td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';

  container.innerHTML = html;

  // Draw sparklines
  allMunis.forEach(m => {
    drawSparkline(`spark_${m.municipio_id}`, m.municipio_id);
  });
}

function drawSparkline(canvasId, muniId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Generate synthetic 3-year trend based on municipio seed
  const seed = muniId.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  const base = (seed % 40) + 30;
  const data = [
    base + (seed % 10) - 5,
    base + (seed % 15) - 3,
    base + (seed % 8) + 2,
  ];

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['2023', '2024', '2025'],
      datasets: [{
        data: data,
        borderColor: '#38bdf8',
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}

/* ===== Contracts ===== */
document.getElementById('loadContracts').addEventListener('click', loadContracts);

async function loadContracts() {
  const muniId = document.getElementById('contractsMuni').value;
  const year = document.getElementById('contractsYear').value;
  if (!muniId) return;

  const container = document.getElementById('contractsTableContainer');
  container.innerHTML = '<p class="placeholder-text">Cargando contratos...</p>';

  let contracts = [];
  try {
    const res = await fetch(`${API_BASE}/municipio/${muniId}/contracts?year=${year}`);
    if (res.ok) {
      const data = await res.json();
      contracts = data.contracts || [];
    } else { throw new Error(); }
  } catch (e) {
    // Fallback: load from static JSON
    try {
      const res = await fetch(`./data/contracts_${muniId}_${year}.json`);
      if (res.ok) contracts = await res.json();
    } catch (e2) { contracts = []; }
  }

  if (contracts.length === 0) {
    container.innerHTML = '<p class="placeholder-text">No hay contratos disponibles para este municipio y año.</p>';
    return;
  }

  let html = '<table class="contracts-table"><thead><tr>';
  html += '<th>ID</th><th>Fecha</th><th>Modalidad</th><th>Proveedor</th><th>Monto (USD)</th><th>Estado</th><th>Enlace</th>';
  html += '</tr></thead><tbody>';

  contracts.forEach(c => {
    const modalidad = c.modalidad || '';
    let modCls = 'modalidad-otra';
    if (modalidad.includes('Licitación')) modCls = 'modalidad-licitacion';
    else if (modalidad.includes('Directa')) modCls = 'modalidad-directa';

    html += `
      <tr>
        <td>${(c.contrato_id || '').substring(0, 20)}</td>
        <td>${c.fecha || ''}</td>
        <td><span class="modalidad-badge ${modCls}">${modalidad}</span></td>
        <td>${(c.proveedor || '').substring(0, 30)}</td>
        <td>$${(c.monto || 0).toLocaleString('es-EC', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        <td>${c.estado || ''}</td>
        <td>${c.url_documento ? `<a href="${c.url_documento}" target="_blank" class="contract-link">Ver →</a>` : '—'}</td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

/* ===== Init ===== */
loadData();
