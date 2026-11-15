/* O2tracker — vanilla JS, no build step. All displayed values come from data/derived/viewer/manifest.json,
   its value-encoded PNG rasters, and data/derived/case_studies.json. Nothing here synthesises observations. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = (x, d = 2) => (x === null || x === undefined || Number.isNaN(x)) ? '—' : Number(x).toFixed(d);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dshort = iso => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]}`; };
const dlong = iso => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };
function el(n, at = {}, txt) { const e = document.createElementNS(NS, n); for (const k in at) e.setAttribute(k, at[k]); if (txt !== undefined) e.textContent = txt; return e; }

/* ---------- colour scales chosen by physical quantity ---------- */
function ramp(stops) { // stops: [[t, r, g, b], ...] t in 0..1
  const lut = new Uint8ClampedArray(256 * 3);
  for (let i = 0; i < 256; i++) {
    const t = i / 255; let k = 0; while (k < stops.length - 2 && t > stops[k + 1][0]) k++;
    const [t0, ...a] = stops[k], [t1, ...b] = stops[k + 1], u = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
    for (let c = 0; c < 3; c++) lut[i * 3 + c] = a[c] + (b[c] - a[c]) * u;
  }
  return lut;
}
const SCALES = {
  gray: { lut: ramp([[0, 12, 14, 16], [1, 250, 250, 248]]), css: 'linear-gradient(90deg,#0c0e10,#fafaf8)' },
  diverging: { lut: ramp([[0, 33, 102, 172], [.5, 247, 247, 247], [1, 178, 88, 24]]), css: 'linear-gradient(90deg,#2166ac,#f7f7f7,#b25818)' },
  cividis: { lut: ramp([[0, 0, 34, 78], [.25, 61, 78, 107], [.5, 124, 123, 120], [.75, 188, 175, 111], [1, 254, 232, 56]]), css: 'linear-gradient(90deg,#00224e,#3d4e6b,#7c7b78,#bcaf6f,#fee838)' },
  phase: { lut: ramp([[0, 49, 54, 149], [.5, 247, 247, 247], [1, 165, 0, 38]]), css: 'linear-gradient(90deg,#313695,#f7f7f7,#a50026)' }
};

/* ---------- inverse UTM (WGS84), for coordinate readout only ---------- */
function utmToLatLon(E, N, zone, south) {
  const a = 6378137, f = 1 / 298.257223563, k0 = 0.9996, e2 = f * (2 - f), ep2 = e2 / (1 - e2);
  const x = E - 500000, y = south ? N - 10000000 : N, M = y / k0;
  const mu = M / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 ** 3 / 256));
  const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));
  const p = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu) + (21 * e1 * e1 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu) + (151 * e1 ** 3 / 96) * Math.sin(6 * mu);
  const C1 = ep2 * Math.cos(p) ** 2, T1 = Math.tan(p) ** 2, N1 = a / Math.sqrt(1 - e2 * Math.sin(p) ** 2), R1 = a * (1 - e2) / (1 - e2 * Math.sin(p) ** 2) ** 1.5, D = x / (N1 * k0);
  const lat = p - (N1 * Math.tan(p) / R1) * (D * D / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * ep2 - 3 * C1 * C1) * D ** 6 / 720);
  const lon = (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * ep2 + 24 * T1 * T1) * D ** 5 / 120) / Math.cos(p);
  return [lat * 180 / Math.PI, (zone - 1) * 6 - 180 + 3 + lon * 180 / Math.PI];
}

/* ---------- state ---------- */
const S = { ref: null, traj: null, sel: null, selAuto: true, selMode: false, dd: null, manifest: null, cases: null, ablation: null, archive: [], site: 'katarapko', layer: 'HH', mode: 'compare', acq: 2, before: 0, after: 1,
  pair: 3, points: true, view: null, split: .5, pick: null, cache: new Map(), images: {}, drag: null };
const canvas = $('map'), ctx = canvas.getContext('2d');

async function json(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + ' → HTTP ' + r.status); return r.json(); }
function loadRaster(file) {
  if (S.cache.has(file)) return S.cache.get(file);
  const p = new Promise((res, rej) => {
    const img = new Image(); img.decoding = 'async';
    img.onload = () => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
      const d = x.getImageData(0, 0, img.width, img.height).data, codes = new Uint8Array(img.width * img.height); for (let i = 0; i < codes.length; i++) codes[i] = d[i * 4]; res({ w: img.width, h: img.height, codes }); };
    img.onerror = () => rej(new Error('Could not load ' + file)); img.src = '/data/derived/viewer/' + file;
  });
  S.cache.set(file, p); return p;
}
const decode = (enc, code) => code === 0 ? null : enc.offset + code * enc.scale;

/* ---------- site configuration ---------- */
const SITE = {
  katarapko: {
    label: 'Katarapko–Pike, South Australia',
    layers: [['HH', 'HH'], ['HV', 'HV']],
    modes: [['single', 'Single date'], ['compare', 'Before / after'], ['difference', 'Difference']],
    display: { HH: [-25, -3], HV: [-32, -12] }, diff: 6,
    lede: 'L-band backscatter (γ⁰), River Murray floodplain: three passes, track 153, same orbit and grid.',
    pointsLabel: 'Show river oxygen stations'
  },
  everglades: {
    label: 'Everglades WCA-3A, Florida',
    layers: [['coherence', 'Coherence'], ['phase', 'Phase']],
    modes: [['single', '12-day pair']],
    lede: 'Coherence and unwrapped phase for 12-day pairs, track 47, WCA-3A, with EDEN gauge locations.',
    pointsLabel: 'Show water-level gauges'
  }
};

/* ---------- controls ---------- */
// Native radio groups: the browser supplies arrow-key movement, a single tab stop and disabled handling.
function seg(container, items, current, onPick, disabled = () => false) {
  const hadFocus = container.contains(document.activeElement), name = container.id;
  container.replaceChildren();
  for (const [v, label] of items) {
    const l = document.createElement('label'), r = document.createElement('input'), t = document.createElement('span');
    r.type = 'radio'; r.name = name; r.value = v; r.checked = v === current; r.disabled = disabled(v); t.textContent = label;
    r.addEventListener('change', () => { if (r.checked) onPick(v); });
    l.append(r, t); container.append(l);
  }
  if (hadFocus) container.querySelector('input:checked')?.focus();
}

function renderControls() {
  const cfg = SITE[S.site], site = S.manifest.sites[S.site];
  seg($('site-seg'), [['katarapko', 'Katarapko–Pike'], ['everglades', 'Everglades']], S.site, v => { if (v !== S.site) { S.site = v; S.layer = v === 'katarapko' ? 'HH' : 'coherence'; S.mode = v === 'katarapko' ? 'compare' : 'single'; S.pick = null; S.view = null; update(); } });
  seg($('layer-seg'), cfg.layers, S.layer, v => { S.layer = v; update(); });
  seg($('mode-seg'), cfg.modes, S.mode, v => { S.mode = v; update(); });
  $('mode-field').hidden = cfg.modes.length < 2;
  $('compare-field').hidden = !(S.site === 'katarapko' && S.mode !== 'single');
  $('split-range').hidden = !(S.site === 'katarapko' && S.mode === 'compare');
  if (S.site === 'katarapko') {
    const opts = site.acquisitions.map((a, i) => `<option value="${i}">${dlong(a.date)} · ${a.time_utc.slice(0, 2)}:${a.time_utc.slice(2, 4)} UTC</option>`).join('');
    $('before-sel').innerHTML = opts; $('after-sel').innerHTML = opts; $('before-sel').value = S.before; $('after-sel').value = S.after;
  }
  $('points-label').textContent = cfg.pointsLabel; $('points-toggle').checked = S.points;
  $('lede').textContent = cfg.lede;
  renderTimeline(); renderLegend(); renderMeta(); renderArea();
}

function renderTimeline() {
  const tl = $('timeline'); tl.replaceChildren();
  const title = document.createElement('span'); title.className = 'tl-title'; tl.append(title);
  if (S.site === 'katarapko') {
    title.textContent = 'NISAR passes, track 153';
    const acqs = S.manifest.sites.katarapko.acquisitions, processed = new Map(acqs.map((a, i) => [a.date, i]));
    let prev = null;
    for (const iso of S.archive) {
      if (prev && (Date.parse(iso) - Date.parse(prev)) / 864e5 > 13) { const g = document.createElement('span'); g.className = 'tick gap'; g.title = 'No acquisition in the archive for this 12-day slot'; g.innerHTML = '<i></i><span>gap</span>'; tl.append(g); }
      prev = iso;
      const b = document.createElement('button'); b.type = 'button'; b.className = 'tick'; b.innerHTML = `<i></i><span>${dshort(iso)}</span>`;
      if (processed.has(iso)) {
        const i = processed.get(iso), on = S.mode === 'single' ? i === S.acq : (i === S.before || i === S.after);
        b.setAttribute('aria-pressed', String(on)); b.title = S.mode === 'single' ? 'Show this acquisition' : 'Use as the nearer end of the comparison';
        // In comparison modes a click moves whichever end (before/after) is nearer to the clicked date.
        b.addEventListener('click', () => {
          if (S.mode === 'single') S.acq = i;
          else if (i !== S.before && i !== S.after) { if (Math.abs(i - S.before) < Math.abs(i - S.after)) S.before = i; else S.after = i; }
          update();
        });
      } else { b.className = 'tick archive'; b.disabled = true; b.title = 'Acquired (ASF archive) but not processed in this release'; b.setAttribute('aria-label', dlong(iso) + ': in archive, not processed here'); }
      tl.append(b);
    }
  } else {
    title.textContent = '12-day pairs, track 47';
    const pairs = S.manifest.sites.everglades.pairs;
    pairs.forEach((p, i) => {
      if (i && Date.parse(p.reference_date) !== Date.parse(pairs[i - 1].secondary_date)) { const g = document.createElement('span'); g.className = 'tick gap'; g.title = 'Gap: the 24-day pair here was not used'; g.innerHTML = '<i></i><span>gap</span>'; tl.append(g); }
      const b = document.createElement('button'); b.type = 'button'; b.className = 'tick'; b.setAttribute('aria-pressed', String(i === S.pair));
      b.innerHTML = `<i></i><span>${dshort(p.reference_date)}–${dshort(p.secondary_date)}</span>`; b.title = p.scored_in_e15 ? 'Pair scored in the E15 evidence test' : 'Pair did not pass the E15 eligibility gate';
      b.addEventListener('click', () => { S.pair = i; S.pick = null; update(); }); tl.append(b);
    });
  }
}

function layerSpec() {
  const site = S.manifest.sites[S.site];
  if (S.site === 'katarapko') {
    const [lo, hi] = SITE.katarapko.display[S.layer];
    if (S.mode === 'difference') return { kind: 'difference', scale: 'diverging', lo: -SITE.katarapko.diff, hi: SITE.katarapko.diff, unit: 'dB', title: `${S.layer} backscatter change, ${dshort(site.acquisitions[S.after].date)} minus ${dshort(site.acquisitions[S.before].date)}`, status: 'DERIVED' };
    return { kind: 'backscatter', scale: 'gray', lo, hi, unit: 'dB', title: `${S.layer} radar backscatter (γ⁰)`, status: 'OBSERVED' };
  }
  if (S.layer === 'coherence') return { kind: 'coherence', scale: 'cividis', lo: 0, hi: 1, unit: '', title: 'Interferometric coherence', status: 'OBSERVED' };
  return { kind: 'phase', scale: 'phase', lo: -8, hi: 8, unit: 'rad', title: 'Unwrapped phase relative to scene median', status: 'OBSERVED' };
}

function renderLegend() {
  const L = layerSpec(), lg = $('legend');
  const lowWord = { backscatter: 'darker', difference: 'decrease', coherence: 'decorrelated', phase: '' }[L.kind];
  const highWord = { backscatter: 'brighter', difference: 'increase', coherence: 'stable', phase: '' }[L.kind];
  lg.innerHTML = `<div class="lg"><strong>${esc(L.title)}${L.unit ? ' (' + L.unit + ')' : ''} <span class="badge ${L.status.toLowerCase()}">${L.status[0] + L.status.slice(1).toLowerCase()}</span></strong>
    <div class="ramp" style="background:${SCALES[L.scale].css}"></div>
    <div class="ends"><span>${String(L.lo).replace('-', '−')}${lowWord ? ' ' + lowWord : ''}</span><span>${L.hi > 0 && (L.kind === 'difference' || L.kind === 'phase') ? '+' : ''}${String(L.hi).replace('-', '−')}${highWord ? ' ' + highWord : ''}</span></div></div>
    <span class="muted small">${L.kind === 'backscatter' || L.kind === 'difference' ? 'Same colour range for every date. ' : ''}Light grey: no valid data.</span>
    <span class="pkey small">${S.site === 'katarapko' ? '<i class="pt ring"></i>River oxygen station' : '<i class="pt fill"></i>Gauge scored in E15 <i class="pt open"></i>Gauge not scored for this pair'}</span>`;
}

function renderMeta() {
  const site = S.manifest.sites[S.site];
  $('explore-h').textContent = SITE[S.site].label;
  const rows = [['Product', site.product], ['Orbit', site.track_frame], ['Pixel size', `${site.display_resolution_m} m display · ${site.native_resolution_m} m source`], ['Grid', `${site.crs}`]];
  if (S.site === 'katarapko') {
    const a = site.acquisitions;
    $('stage-sub').textContent = S.mode === 'single' ? `${dlong(a[S.acq].date)} · 20:34 UTC · ${S.layer} polarization` : `${dlong(a[S.before].date)} and ${dlong(a[S.after].date)} · ${S.layer} polarization · same orbit, same grid`;
    $('caveat').innerHTML = '<strong>Caveat:</strong> radar-observed changes are not automatically flooding. Provisional product; reference targets elsewhere in the scene also changed between dates, so a common radiometric shift cannot be ruled out.';
  } else {
    const p = site.pairs[S.pair];
    $('stage-sub').textContent = `${dlong(p.reference_date)} to ${dlong(p.secondary_date)}; median coherence ${fmt(p.median_coherence, 2)}; ${p.scored_in_e15 ? 'scored in E15' : 'not eligible for E15'}`;
    rows.push(['Granule', p.granule_id]);
    $('caveat').innerHTML = '<strong>Caveat:</strong> phase is shown relative to the scene median with no atmospheric or tide correction; it is not converted to water level here. Gauge estimates are from the exploratory E15 test.';
  }
  $('meta').innerHTML = rows.map(r => `<dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd>`).join('');
  renderProvenance();
}

/* ---------- full provenance (inline, follows the selected site and pair) ---------- */
function renderProvenance() {
  const site = S.manifest.sites[S.site]; let rows = [['Site', site.name], ['Quantity', site.quantity], ['Status', site.status], ['Processing', site.processing]];
  if (S.site === 'katarapko') { site.acquisitions.forEach(a => rows.push([dlong(a.date), `${a.granule_id}; HH SHA-256 ${a.source_sha256.HHHH.slice(0, 12)}…`])); rows.push(['Comparison check', `Same orbit/frame and mode, identical grid, registration offset 0 px. ${site.comparability.caveats.join('; ')}.`]); }
  else { const p = site.pairs[S.pair]; rows.push(['Concept ID', p.concept_id], ['Phase note', site.phase_to_los_note], ['Source SHA-256', `coherence ${p.source_sha256.coherenceMagnitude.slice(0, 12)}…, phase ${p.source_sha256.unwrappedPhase.slice(0, 12)}…`]); }
  rows.push(['Data access', 'NASA/ISRO NISAR via the NASA Alaska Satellite Facility DAAC (open data). Provisional products.'], ['Display encoding', S.manifest.encoding_note]);
  $('info-body').innerHTML = rows.map(r => `<dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd>`).join('');
}

/* ---------- raster composition ---------- */
async function compose() {
  const site = S.manifest.sites[S.site], L = layerSpec(), lut = SCALES[L.scale].lut;
  const make = async (layers, colorFn) => {
    const rs = await Promise.all(layers.map(l => loadRaster(l.file)));
    const { w, h } = rs[0], c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d'), im = x.createImageData(w, h), d = im.data;
    for (let i = 0; i < w * h; i++) {
      const v = colorFn(rs.map(r => r.codes[i]));
      if (v === null) { d[i * 4 + 3] = 0; continue; }
      const k = Math.max(0, Math.min(255, Math.round((v - L.lo) / (L.hi - L.lo) * 255))) * 3;
      d[i * 4] = lut[k]; d[i * 4 + 1] = lut[k + 1]; d[i * 4 + 2] = lut[k + 2]; d[i * 4 + 3] = 255;
    }
    x.putImageData(im, 0, 0); return { canvas: c, rasters: rs, layers };
  };
  if (S.site === 'katarapko') {
    const A = site.acquisitions, lay = i => A[i].layers[S.layer];
    if (S.mode === 'single') return { left: await make([lay(S.acq)], ([c]) => decode(lay(S.acq), c)) };
    if (S.mode === 'compare') return { left: await make([lay(S.before)], ([c]) => decode(lay(S.before), c)), right: await make([lay(S.after)], ([c]) => decode(lay(S.after), c)) };
    const b = lay(S.before), a = lay(S.after);
    return { left: await make([b, a], ([cb, ca]) => (cb && ca) ? decode(a, ca) - decode(b, cb) : null) };
  }
  const p = site.pairs[S.pair], l = p.layers[S.layer];
  return { left: await make([l], ([c]) => decode(l, c)) };
}

/* ---------- drawing ---------- */
function fit() {
  const site = S.manifest.sites[S.site], r = canvas.getBoundingClientRect();
  const s = Math.min(r.width / site.width, r.height / site.height) * .96;
  S.view = { s, tx: (r.width - site.width * s) / 2, ty: (r.height - site.height * s) / 2 };
}
function draw() {
  const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  if (canvas.width !== Math.round(r.width * dpr) || canvas.height !== Math.round(r.height * dpr)) { canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr); }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, r.width, r.height);
  if (!S.images.left || !S.view) return;
  const { s, tx, ty } = S.view, site = S.manifest.sites[S.site];
  ctx.imageSmoothingEnabled = s < 2;
  ctx.fillStyle = '#d9dce1'; ctx.fillRect(tx, ty, site.width * s, site.height * s);
  ctx.drawImage(S.images.left.canvas, tx, ty, site.width * s, site.height * s);
  const compare = S.site === 'katarapko' && S.mode === 'compare' && S.images.right;
  if (compare) {
    const xs = r.width * S.split; ctx.save(); ctx.beginPath(); ctx.rect(xs, 0, r.width - xs, r.height); ctx.clip();
    ctx.fillStyle = '#d9dce1'; ctx.fillRect(tx, ty, site.width * s, site.height * s); ctx.drawImage(S.images.right.canvas, tx, ty, site.width * s, site.height * s); ctx.restore();
    const h = $('split-handle'); h.hidden = false; h.style.left = xs + 'px';
  } else $('split-handle').hidden = true;
  if (S.points) drawPoints();
  drawSel();
  if (S.pick) { const [px, py] = toScreen(S.pick.col + .5, S.pick.row + .5); ctx.strokeStyle = '#17191c'; ctx.lineWidth = 1.5; ctx.strokeRect(px - 6, py - 6, 12, 12); ctx.strokeStyle = '#fff'; ctx.strokeRect(px - 7.5, py - 7.5, 15, 15); }
  // scale bar
  const mpp = site.display_resolution_m / s, nice = [100, 200, 500, 1000, 2000, 5000, 10000, 20000].find(m => m / mpp >= 70) || 20000;
  $('scalebar').querySelector('span').style.width = (nice / mpp) + 'px'; $('scalebar').querySelector('em').textContent = nice >= 1000 ? nice / 1000 + ' km' : nice + ' m';
}
const toScreen = (col, row) => [S.view.tx + col * S.view.s, S.view.ty + row * S.view.s];
const pxOf = (x, y) => { const t = S.manifest.sites[S.site].transform; return [(x - t[2]) / t[0], (y - t[5]) / t[4]]; };
function pointsList() {
  const site = S.manifest.sites[S.site];
  return S.site === 'katarapko' ? site.points : site.pairs[S.pair].gauges;
}
function drawPoints() {
  for (const p of pointsList()) {
    const [c, rr] = pxOf(p.x, p.y), [x, y] = toScreen(c, rr);
    ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2);
    // black/white marks stay legible on both the grayscale and the cividis/phase ramps
    if (S.site === 'katarapko' || !p.scored_e15) { ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#111'; ctx.stroke(); }
    else { ctx.fillStyle = '#111'; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke(); }
    if (S.pick && S.pick.point === p.id) { ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2); ctx.strokeStyle = '#17191c'; ctx.lineWidth = 1.5; ctx.stroke(); }
  }
}

/* ---------- readout ---------- */
function inspectAt(sx, sy) {
  const site = S.manifest.sites[S.site];
  if (S.points) for (const p of pointsList()) { const [c, rr] = pxOf(p.x, p.y), [x, y] = toScreen(c, rr); if (Math.hypot(x - sx, y - sy) <= 9) { S.pick = { col: Math.floor(c), row: Math.floor(rr), point: p.id }; readout(); draw(); return; } }
  const col = Math.floor((sx - S.view.tx) / S.view.s), row = Math.floor((sy - S.view.ty) / S.view.s);
  if (col < 0 || row < 0 || col >= site.width || row >= site.height) { S.pick = null; readout(); draw(); return; }
  S.pick = { col, row }; readout(); draw();
}
function readout() {
  const box = $('readout');
  if (!S.pick) { box.innerHTML = '<p class="label">Pixel values</p><p class="muted">Click a pixel to show its values.</p>'; return; }
  const site = S.manifest.sites[S.site], t = site.transform, { col, row } = S.pick, i = row * site.width + col;
  const X = t[2] + (col + .5) * t[0], Y = t[5] + (row + .5) * t[4], [lat, lon] = utmToLatLon(X, Y, site.utm_zone, site.south);
  const val = (enc, rast) => decode(enc, rast.codes[i]);
  let rows = [];
  if (S.site === 'katarapko') {
    const A = site.acquisitions;
    A.forEach(a => rows.push([`${S.layer} ${dshort(a.date)}`, loadRaster(a.layers[S.layer].file)]));
    Promise.all(rows.map(r => r[1])).then(rs => {
      const vals = rs.map((r, k) => val(A[k].layers[S.layer], r));
      let html = vals.map((v, k) => `<tr><td>${esc(S.layer)} · ${dlong(A[k].date)}</td><td>${v === null ? 'no data' : fmt(v, 1) + ' dB'}</td></tr>`).join('');
      if (vals[S.before] !== null && vals[S.after] !== null && S.mode !== 'single') html += `<tr><td>Change ${dshort(A[S.after].date)} − ${dshort(A[S.before].date)}</td><td>${(vals[S.after] - vals[S.before] >= 0 ? '+' : '') + fmt(vals[S.after] - vals[S.before], 1)} dB</td></tr>`;
      finish(html);
    });
  } else {
    const p = site.pairs[S.pair];
    Promise.all([loadRaster(p.layers.coherence.file), loadRaster(p.layers.phase.file)]).then(([rc, rp]) => {
      let html = `<tr><td>Coherence</td><td>${val(p.layers.coherence, rc) === null ? 'no data' : fmt(val(p.layers.coherence, rc), 2)}</td></tr><tr><td>Phase vs scene median</td><td>${val(p.layers.phase, rp) === null ? 'no data / unwrapping gap' : fmt(val(p.layers.phase, rp), 2) + ' rad'}</td></tr>`;
      finish(html);
    });
  }
  function finish(html) {
    let pt = '';
    const p = S.pick.point && pointsList().find(q => q.id === S.pick.point);
    if (p && S.site === 'katarapko') pt = `<p class="label" style="margin-top:12px">${esc(p.id)}</p><p class="small">${esc(p.name)} (${esc(p.kind)}). Its oxygen record is in the Katarapko investigation; distance is not hydraulic connection.</p>`;
    if (p && S.site === 'everglades') pt = `<p class="label" style="margin-top:12px">Gauge ${esc(p.id)}, ${esc(p.agency)}</p><table><tr><td>Vegetation</td><td>${esc(p.vegetation)}</td></tr><tr><td><span class="badge observed">Observed</span> 12-day change</td><td>${p.observed_change_cm === null ? 'no observed stage' : fmt(p.observed_change_cm, 1) + ' cm'}</td></tr>${p.scored_e15 ? `<tr><td><span class="badge exploratory">Exploratory</span> NISAR-assisted</td><td>${fmt(p.nisar_estimate_cm, 1)} cm</td></tr><tr><td>Gauge-only baseline</td><td>${fmt(p.baseline_estimate_cm, 1)} cm</td></tr>` : `<tr><td>E15 test</td><td>${p.eligible_e15 ? 'eligible' : 'not eligible this pair'}</td></tr>`}</table>`;
    box.innerHTML = `<p class="label">Pixel ${col}, ${row} <span class="badge observed">Observed</span></p><table>${html}</table><p class="coords" style="margin-top:8px">${lat.toFixed(4)}°, ${lon.toFixed(4)}°<br>UTM ${site.utm_zone}${site.south ? 'S' : 'N'} ${Math.round(X)} E ${Math.round(Y)} N</p>${pt}<p class="small muted">Values decoded from 8-bit display rasters (±${fmt(S.site === 'katarapko' ? site.acquisitions[0].layers.HH.scale / 2 : site.pairs[0].layers.coherence.scale / 2, 3)}).</p>`;
  }
}

/* ---------- area analysis (client-side, exact on the stored integer codes) ---------- */
const CAVEAT_TEXT = 'Radar-observed changes are not automatically flooding. Provisional product; reference targets elsewhere in the scene also changed between dates, so a common radiometric shift cannot be ruled out.';
const AREA_MIN_PX = 25, BLOCK = 48; // starting block: 48 × 48 px = 1.9 km, large enough to see at full view
const boxActive = () => S.site === 'katarapko' && S.mode !== 'single';
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const normSel = s => ({ c0: Math.min(s.c0, s.c1), r0: Math.min(s.r0, s.r1), c1: Math.max(s.c0, s.c1), r1: Math.max(s.r0, s.r1) });
const ddKey = () => [S.before, S.after, S.layer].join('|');
const dBtxt = v => { const r = Math.round(v * 10) / 10; return (r < 0 ? '−' : r > 0 ? '+' : '') + Math.abs(r).toFixed(1) + ' dB'; };
const num = v => { const r = Math.round(v * 10) / 10; return (r < 0 ? '−' : '') + Math.abs(r).toFixed(1); };
// value at quantile q of a histogram (linear interpolation between ranks), returned as a bin index
function hq(h, n, q) {
  const k = (n - 1) * q, lo = Math.floor(k), hi = Math.ceil(k); let acc = 0, a = null, b = null;
  for (let i = 0; i < h.length; i++) { acc += h[i]; if (a === null && acc > lo) a = i; if (acc > hi) { b = i; break; } }
  return a + (b - a) * (k - lo);
}
// Per-pixel change (After minus Before) is offset difference + (code_after - code_before) × scale: exact, no float sorting.
async function ensureDD() {
  const key = ddKey(); if (S.dd && S.dd.key === key) return S.dd;
  const A = S.manifest.sites.katarapko.acquisitions, eb = A[S.before].layers[S.layer], ea = A[S.after].layers[S.layer];
  if (eb.scale !== ea.scale) throw new Error('Before and After encodings differ');
  const [rb, ra] = await Promise.all([loadRaster(eb.file), loadRaster(ea.file)]);
  const { w, h } = rb, scene = new Uint32Array(511); let sceneN = 0, sceneClipped = 0;
  for (let i = 0; i < w * h; i++) { const cb = rb.codes[i], ca = ra.codes[i]; if (!cb || !ca) continue; scene[ca - cb + 255]++; sceneN++; if (cb === 1 || cb === 255 || ca === 1 || ca === 255) sceneClipped++; }
  const dd = { key, w, h, rb: rb.codes, ra: ra.codes, scale: ea.scale, offDiff: ea.offset - eb.offset, scene, sceneN, sceneClipped };
  dd.sceneMed = (hq(scene, sceneN, .5) - 255) * dd.scale + dd.offDiff;
  if (key !== ddKey()) return null; // selection changed while loading
  S.dd = dd;
  if (S.selAuto) startBox(dd);
  return dd;
}
// Starting box: the fully valid BLOCK × BLOCK block with the largest mean change for this layer and these dates.
function startBox(dd) {
  let best = null;
  // the block and a one-block margin around it must be fully valid, which keeps the start away from swath edges
  for (let r = BLOCK; r + 2 * BLOCK <= dd.h; r += BLOCK) for (let c = BLOCK; c + 2 * BLOCK <= dd.w; c += BLOCK) {
    let sum = 0, ok = true;
    for (let y = -BLOCK; y < 2 * BLOCK && ok; y++) for (let x = -BLOCK; x < 2 * BLOCK; x++) { const i = (r + y) * dd.w + c + x, cb = dd.rb[i], ca = dd.ra[i]; if (!cb || !ca) { ok = false; break; } if (y >= 0 && y < BLOCK && x >= 0 && x < BLOCK) sum += ca - cb; }
    if (ok && (!best || Math.abs(sum) > Math.abs(best.sum))) best = { sum, c, r };
  }
  if (best) S.sel = { c0: best.c, r0: best.r, c1: best.c + BLOCK, r1: best.r + BLOCK };
}
function boxStats(dd, s) {
  const c0 = clamp(Math.floor(s.c0), 0, dd.w), c1 = clamp(Math.ceil(s.c1), 0, dd.w), r0 = clamp(Math.floor(s.r0), 0, dd.h), r1 = clamp(Math.ceil(s.r1), 0, dd.h);
  const hist = new Uint32Array(511); let n = 0, clipped = 0;
  for (let r = r0; r < r1; r++) for (let c = c0; c < c1; c++) { const i = r * dd.w + c, cb = dd.rb[i], ca = dd.ra[i]; if (!cb || !ca) continue; hist[ca - cb + 255]++; n++; if (cb === 1 || cb === 255 || ca === 1 || ca === 255) clipped++; }
  const v = q => n ? (hq(hist, n, q) - 255) * dd.scale + dd.offDiff : null;
  return { box: { c0, r0, c1, r1 }, total: Math.max(0, (c1 - c0) * (r1 - r0)), n, clipped, hist, med: v(.5), q25: v(.25), q75: v(.75) };
}
// Comparison basis: the reference box if the user set one, otherwise the whole scene.
function compStats(dd) {
  if (S.ref) { const r = boxStats(dd, S.ref); return { med: r.n >= AREA_MIN_PX ? r.med : null, label: 'Reference area', n: r.n, stats: r }; }
  return { med: dd.sceneMed, label: 'Whole scene', n: dd.sceneN, stats: null };
}
// Trajectory: median backscatter level of a box on each of the three dates (current layer).
async function ensureTraj() {
  if (S.traj && S.traj.key === S.layer) return S.traj;
  const A = S.manifest.sites.katarapko.acquisitions, encs = A.map(a => a.layers[S.layer]), rs = await Promise.all(encs.map(e => loadRaster(e.file)));
  const scene = rs.map((r, k) => { const h = new Uint32Array(256); let n = 0; for (let i = 0; i < r.codes.length; i++) { const c = r.codes[i]; if (c) { h[c]++; n++; } } return encs[k].offset + hq(h, n, .5) * encs[k].scale; });
  S.traj = { key: S.layer, rs, encs, w: rs[0].w, h: rs[0].h, scene }; return S.traj;
}
function boxSeries(tr, s) {
  const c0 = clamp(Math.floor(s.c0), 0, tr.w), c1 = clamp(Math.ceil(s.c1), 0, tr.w), r0 = clamp(Math.floor(s.r0), 0, tr.h), r1 = clamp(Math.ceil(s.r1), 0, tr.h);
  return tr.rs.map((r, k) => { const h = new Uint32Array(256); let n = 0; for (let y = r0; y < r1; y++) for (let x = c0; x < c1; x++) { const c = r.codes[y * tr.w + x]; if (c) { h[c]++; n++; } } return n >= AREA_MIN_PX ? tr.encs[k].offset + hq(h, n, .5) * tr.encs[k].scale : null; });
}
function renderTraj() {
  const svg = $('traj'), tr = S.traj; svg.replaceChildren();
  if (!tr || tr.key !== S.layer || !S.sel) { svg.toggleAttribute('hidden', true); return; }
  const A = S.manifest.sites.katarapko.acquisitions, area = boxSeries(tr, S.sel), cmp = S.ref ? boxSeries(tr, S.ref) : tr.scene;
  if (area.some(v => v === null)) { svg.toggleAttribute('hidden', true); return; }
  svg.toggleAttribute('hidden', false);
  const W = 640, H = 170, L = 62, R = 118, T = 16, B = 28, vals = area.concat(cmp.filter(v => v !== null));
  const lo = Math.floor(Math.min(...vals)) - 1, hi = Math.ceil(Math.max(...vals)) + 1, t = A.map(a => Date.parse(a.date));
  const X = i => L + (t[i] - t[0]) / (t[2] - t[0]) * (W - L - R), Y = v => T + (hi - v) / (hi - lo) * (H - T - B);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const add = (n, at, txt) => { const e = el(n, at, txt); svg.append(e); return e; };
  const g = add('defs').appendChild(el('linearGradient', { id: 'g-area', x1: 0, y1: 0, x2: 0, y2: 1 }));
  g.append(el('stop', { offset: '0%', 'stop-color': '#1f5fa8', 'stop-opacity': .28 }), el('stop', { offset: '100%', 'stop-color': '#1f5fa8', 'stop-opacity': 0 }));
  for (const v of [lo, (lo + hi) / 2, hi]) { add('line', { x1: L, x2: W - R + 8, y1: Y(v), y2: Y(v), stroke: '#e6e8ec' }); add('text', { x: L - 8, y: Y(v) + 4, 'text-anchor': 'end', class: 'tk' }, num(v) + (v === hi ? ' dB' : '')); }
  const pts = a => a.map((v, i) => v === null ? null : [X(i), Y(v)]).filter(Boolean);
  const pa = pts(area);
  add('path', { d: `M${pa.map(p => p.join(',')).join('L')}L${pa[pa.length - 1][0]},${H - B}L${pa[0][0]},${H - B}Z`, fill: 'url(#g-area)' });
  const pc = pts(cmp), cc = S.ref ? '#c2620f' : '#8a9099';
  if (pc.length > 1) add('polyline', { points: pc.map(p => p.join(',')).join(' '), fill: 'none', stroke: cc, 'stroke-width': 2, 'stroke-dasharray': '5 4' });
  add('polyline', { points: pa.map(p => p.join(',')).join(' '), fill: 'none', stroke: '#1f5fa8', 'stroke-width': 2.5, 'stroke-linejoin': 'round' });
  for (const [list, col] of [[cmp, cc], [area, '#1f5fa8']]) list.forEach((v, i) => { if (v === null) return; const on = i === S.before || i === S.after; add('circle', { cx: X(i), cy: Y(v), r: on ? 5 : 3.5, fill: on ? col : '#fff', stroke: col, 'stroke-width': 2 }); });
  A.forEach((a, i) => add('text', { x: X(i), y: H - 8, 'text-anchor': i === 0 ? 'start' : i === 2 ? 'end' : 'middle', class: 'tk' }, dshort(a.date)));
  let ya = Y(area[2]), yc = cmp[2] === null ? null : Y(cmp[2]); if (yc !== null && Math.abs(ya - yc) < 16) { if (ya < yc) { ya -= 8; yc += 8; } else { ya += 8; yc -= 8; } }
  add('text', { x: X(2) + 10, y: ya + 4, class: 'lab', fill: '#1f5fa8' }, 'This area');
  if (yc !== null) add('text', { x: X(2) + 10, y: yc + 4, class: 'lab', fill: cc }, S.ref ? 'Reference' : 'Whole scene');
  svg.setAttribute('aria-label', `Median ${S.layer} backscatter on each date. This area: ${area.map(num).join(', ')} dB. ${S.ref ? 'Reference' : 'Whole scene'}: ${cmp.map(v => v === null ? 'no data' : num(v)).join(', ')} dB.`);
}
function renderArea(announce = false) {
  const kat = S.site === 'katarapko', panel = $('area');
  $('sel-toggle').hidden = !boxActive(); if (!boxActive() && S.selMode) setSelMode(false);
  panel.hidden = kat && S.mode === 'single';
  if (panel.hidden) return;
  for (const id of ['area-nums', 'area-actions', 'a-note', 'traj']) $(id).toggleAttribute('hidden', !kat); // toggleAttribute also works on the SVG
  if (!kat) { $('a-detail').textContent = 'Area change needs two backscatter dates of the same ground, which the Katarapko–Pike site has.'; $('a-msg').textContent = ''; return; }
  const dd = S.dd; if (!dd || dd.key !== ddKey()) return;
  const cmp = compStats(dd), cmpTxt = cmp.med === null ? '—' : dBtxt(cmp.med);
  $('a-cmp-l').textContent = cmp.label; $('a-diff-l').textContent = S.ref ? 'Area minus reference' : 'Area minus scene';
  $('a-note').textContent = S.ref ? 'Compared with your reference box (dashed orange). Choose a reference you expect did not change.' : 'Whole scene is the median change across the entire image, not a calibrated correction. For a closer comparison, set a reference box on ground you expect did not change.';
  $('set-ref').hidden = !S.sel; $('clear-ref').hidden = !S.ref;
  const off = !S.sel; $('dl-json').disabled = $('dl-csv').disabled = $('sel-clear').disabled = off;
  $('a-scene').textContent = cmpTxt; renderTraj();
  if (off) { $('a-area').textContent = $('a-diff').textContent = '·'; $('a-detail').textContent = S.ref ? 'Reference set. Now draw the area you want to compare.' : 'Turn on Select area and drag on the map to measure a region.'; if (announce && S.ref) $('a-msg').textContent = 'Reference set. Draw the area to compare.'; return; }
  const st = boxStats(dd, S.sel), A = S.manifest.sites.katarapko.acquisitions;
  if (st.n < AREA_MIN_PX) { $('a-area').textContent = $('a-diff').textContent = '—'; $('a-detail').textContent = `Too few valid pixels (${st.n}). Draw a larger box.`; if (announce) $('a-msg').textContent = 'Too few valid pixels in the selected area.'; return; }
  const diff = cmp.med === null ? null : st.med - cmp.med;
  $('a-area').textContent = dBtxt(st.med); $('a-diff').textContent = diff === null ? '—' : dBtxt(diff);
  $('a-detail').textContent = `${S.layer}, ${dshort(A[S.before].date)} to ${dshort(A[S.after].date)}, ${st.n.toLocaleString('en-US')} pixels, middle half ${num(st.q25)} to ${num(st.q75)} dB${S.selAuto ? `. Starting box: the strongest ${BLOCK} × ${BLOCK} pixel block in the scene` : ''}`;
  if (announce) $('a-msg').textContent = `Selected area: ${dBtxt(st.med)}; ${cmp.label.toLowerCase()} ${cmpTxt}; difference ${diff === null ? 'not available' : dBtxt(diff)}.`;
}
function setSelMode(on) { S.selMode = on; $('sel-toggle').setAttribute('aria-pressed', String(on)); canvas.classList.toggle('sel-mode', on); draw(); }
function drawSel() {
  if (!boxActive() || !S.view) return;
  if (S.ref) { const s = S.ref, [x0, y0] = toScreen(s.c0, s.r0), [x1, y1] = toScreen(s.c1, s.r1);
    ctx.setLineDash([6, 4]); ctx.lineWidth = 3; ctx.strokeStyle = '#fff'; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.lineWidth = 2; ctx.strokeStyle = '#c2620f'; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0); ctx.setLineDash([]);
    ctx.font = '600 12px "IBM Plex Sans", sans-serif'; const tw = ctx.measureText('Reference').width; ctx.fillStyle = '#c2620f'; ctx.fillRect(x0, y0 - 18, tw + 10, 18); ctx.fillStyle = '#fff'; ctx.fillText('Reference', x0 + 5, y0 - 5); }
  if (!S.sel) return;
  const s = normSel(S.sel), [x0, y0] = toScreen(s.c0, s.r0), [x1, y1] = toScreen(s.c1, s.r1);
  ctx.fillStyle = 'rgba(255,255,255,.14)'; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.lineWidth = 3; ctx.strokeStyle = '#fff'; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
  ctx.lineWidth = 1.5; ctx.strokeStyle = '#1f5fa8'; ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
  if (S.selMode) for (const [hx, hy] of [[x0, y0], [x1, y0], [x0, y1], [x1, y1]]) { ctx.fillStyle = '#fff'; ctx.fillRect(hx - 4, hy - 4, 8, 8); ctx.strokeStyle = '#111'; ctx.lineWidth = 1; ctx.strokeRect(hx - 4, hy - 4, 8, 8); }
}
const toPix = (x, y) => { const site = S.manifest.sites[S.site]; return { c: clamp((x - S.view.tx) / S.view.s, 0, site.width), r: clamp((y - S.view.ty) / S.view.s, 0, site.height) }; };
// null = outside, 'move' = inside, otherwise the edges under the pointer ({l,r,t,b})
function hitBox(x, y) {
  if (!S.sel) return null; const s = normSel(S.sel), [x0, y0] = toScreen(s.c0, s.r0), [x1, y1] = toScreen(s.c1, s.r1), tol = 8;
  const inY = y > y0 - tol && y < y1 + tol, inX = x > x0 - tol && x < x1 + tol;
  const e = { l: inY && Math.abs(x - x0) <= tol, r: inY && Math.abs(x - x1) <= tol, t: inX && Math.abs(y - y0) <= tol, b: inX && Math.abs(y - y1) <= tol };
  if (e.l || e.r || e.t || e.b) return e;
  return x > x0 && x < x1 && y > y0 && y < y1 ? 'move' : null;
}
function dragBox(x, y) {
  const d = S.drag, p = toPix(x, y), site = S.manifest.sites[S.site]; S.selAuto = false;
  if (d.kind === 'box-new') { const p0 = toPix(d.sx, d.sy); S.sel = { c0: p0.c, r0: p0.r, c1: p.c, r1: p.r }; }
  else if (d.kind === 'box-move') { const p0 = toPix(d.sx, d.sy), o = d.orig, w = o.c1 - o.c0, h = o.r1 - o.r0, c0 = clamp(o.c0 + p.c - p0.c, 0, site.width - w), r0 = clamp(o.r0 + p.r - p0.r, 0, site.height - h); S.sel = { c0, r0, c1: c0 + w, r1: r0 + h }; }
  else { const o = { ...d.orig }; if (d.hit.l) o.c0 = p.c; if (d.hit.r) o.c1 = p.c; if (d.hit.t) o.r0 = p.r; if (d.hit.b) o.r1 = p.r; S.sel = o; }
  renderArea(false);
}
function keyBox(e) { // Shift+arrows move the box, Shift+Alt+arrows resize it (right/down grow)
  const site = S.manifest.sites[S.site], st = 4, s = normSel(S.sel), dx = { ArrowLeft: -st, ArrowRight: st }[e.key] || 0, dy = { ArrowUp: -st, ArrowDown: st }[e.key] || 0;
  if (e.altKey) S.sel = { ...s, c1: clamp(s.c1 + dx, s.c0 + 1, site.width), r1: clamp(s.r1 + dy, s.r0 + 1, site.height) };
  else { const w = s.c1 - s.c0, h = s.r1 - s.r0, c0 = clamp(s.c0 + dx, 0, site.width - w), r0 = clamp(s.r0 + dy, 0, site.height - h); S.sel = { c0, r0, c1: c0 + w, r1: r0 + h }; }
  S.selAuto = false; renderArea(true); draw();
}
function areaReport() {
  const dd = S.dd, site = S.manifest.sites.katarapko, A = site.acquisitions, st = boxStats(dd, S.sel), t = site.transform, b = st.box;
  const acq = i => ({ date: A[i].date, time_utc: A[i].time_utc, granule_id: A[i].granule_id, source_sha256: A[i].source_sha256 });
  const r3 = v => v === null ? null : Math.round(v * 1000) / 1000;
  return {
    report: 'O2tracker selected-area report', generated_utc: new Date().toISOString(), site: site.name, product: site.product, layer: S.layer,
    before: acq(S.before), after: acq(S.after),
    box: { pixel: { col_min: b.c0, col_max_exclusive: b.c1, row_min: b.r0, row_max_exclusive: b.r1 }, utm: { crs: site.crs, easting_min: t[2] + b.c0 * t[0], easting_max: t[2] + b.c1 * t[0], northing_max: t[5] + b.r0 * t[4], northing_min: t[5] + b.r1 * t[4] }, pixel_size_m: site.display_resolution_m,
      selection: S.selAuto ? `Chosen automatically as the strongest ${BLOCK} × ${BLOCK} pixel block in the scene (largest mean change). It is a selected maximum, not a typical area.` : 'Drawn by the user.' },
    results_db: { this_area_median: r3(st.med), whole_scene_median: r3(dd.sceneMed), area_minus_scene: r3(st.med === null ? null : st.med - dd.sceneMed), this_area_middle_half: [r3(st.q25), r3(st.q75)],
      reference_median: S.ref ? r3(compStats(dd).med) : null, area_minus_reference: S.ref && compStats(dd).med !== null && st.med !== null ? r3(st.med - compStats(dd).med) : null },
    reference_box: S.ref ? { pixel: { col_min: Math.floor(S.ref.c0), col_max_exclusive: Math.ceil(S.ref.c1), row_min: Math.floor(S.ref.r0), row_max_exclusive: Math.ceil(S.ref.r1) }, valid_pixels: compStats(dd).n, note: 'Chosen by the user as ground expected not to change.' } : null,
    trajectory_db: S.traj && S.traj.key === S.layer ? { note: 'Median backscatter level (not change) on each date, pixels valid on that date.', dates: A.map(a => a.date), this_area: boxSeries(S.traj, S.sel).map(r3), whole_scene: S.traj.scene.map(r3), reference: S.ref ? boxSeries(S.traj, S.ref).map(r3) : null } : null,
    statistic: 'Median of per-pixel (After minus Before) backscatter change in dB, computed exactly on the stored integer display codes. Area minus scene is relative to the scene-wide median, which may itself contain real widespread change; it is not a calibrated correction.',
    precision_db: dd.scale,
    pixels: { in_box: st.total, valid: st.n, excluded_nodata: st.total - st.n, at_clip_limits_in_box: st.clipped, scene_valid: dd.sceneN, scene_at_clip_limits: dd.sceneClipped },
    histogram: { bin_width_db: dd.scale, first_bin_db: r3(-255 * dd.scale + dd.offDiff), counts: Array.from(st.hist) },
    statement: 'A candidate to check in the field or with other data, not a finding. A radar backscatter change is not by itself a flooding change, and this is not an oxygen measurement.',
    caveat: CAVEAT_TEXT, encoding_note: S.manifest.encoding_note
  };
}
function download(name, text, type) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0); }
$('dl-json').addEventListener('click', () => { if (S.sel && S.dd) download('o2tracker-area-report.json', JSON.stringify(areaReport(), null, 2), 'application/json'); });
$('dl-csv').addEventListener('click', () => {
  if (!S.sel || !S.dd) return; const r = areaReport(), q = s => `"${String(s).replace(/"/g, '""')}"`;
  const rows = [['quantity', 'value', 'unit'], ['this_area_median', r.results_db.this_area_median, 'dB'], ['whole_scene_median', r.results_db.whole_scene_median, 'dB'], ['area_minus_scene', r.results_db.area_minus_scene, 'dB'],
    ['reference_median', r.results_db.reference_median ?? '', 'dB'], ['area_minus_reference', r.results_db.area_minus_reference ?? '', 'dB'], ['valid_pixels', r.pixels.valid, 'count'], ['layer', r.layer, ''], ['before', r.before.date, ''], ['after', r.after.date, ''], ['box_pixels', `${r.box.pixel.col_min}-${r.box.pixel.col_max_exclusive},${r.box.pixel.row_min}-${r.box.pixel.row_max_exclusive}`, 'col,row'], ['statement', r.statement, '']];
  download('o2tracker-area-report.csv', rows.map(x => x.map(q).join(',')).join('\n'), 'text/csv');
});
$('sel-toggle').addEventListener('click', () => setSelMode(!S.selMode));
$('set-ref').addEventListener('click', () => { if (!S.sel) return; S.ref = normSel(S.sel); S.sel = null; S.selAuto = false; setSelMode(true); renderArea(true); draw(); });
$('clear-ref').addEventListener('click', () => { S.ref = null; renderArea(true); draw(); });
$('sel-clear').addEventListener('click', () => { S.sel = null; S.selAuto = false; renderArea(true); draw(); });

/* ---------- update cycle ---------- */
let token = 0;
async function update() {
  const my = ++token; renderControls(); $('map-loading').hidden = false; $('map-error').hidden = true;
  try {
    const imgs = await compose(); if (my !== token) return;
    S.images = imgs; if (!S.view) fit();
    $('label-left').textContent = labelLeft(); const right = S.site === 'katarapko' && S.mode === 'compare';
    $('label-right').hidden = !right; if (right) $('label-right').textContent = `After · ${dlong(S.manifest.sites.katarapko.acquisitions[S.after].date)}`;
    if (boxActive()) { await ensureDD(); await ensureTraj(); } if (my !== token) return;
    draw(); readout(); renderArea();
  } catch (e) { $('map-error').hidden = false; $('map-error').textContent = 'Radar layer could not be loaded. ' + e.message; }
  finally { if (my === token) $('map-loading').hidden = true; }
}
function labelLeft() {
  const s = S.manifest.sites[S.site];
  if (S.site === 'everglades') { const p = s.pairs[S.pair]; return `${dshort(p.reference_date)}–${dshort(p.secondary_date)} 2026`; }
  if (S.mode === 'single') return dlong(s.acquisitions[S.acq].date);
  if (S.mode === 'compare') return `Before · ${dlong(s.acquisitions[S.before].date)}`;
  return `${dshort(s.acquisitions[S.after].date)} − ${dshort(s.acquisitions[S.before].date)}`;
}

/* ---------- pointer & keyboard ---------- */
canvas.addEventListener('pointerdown', e => {
  const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  const nearSplit = S.site === 'katarapko' && S.mode === 'compare' && Math.abs(x - r.width * S.split) < 14;
  let kind = null, hit = null;
  if (!nearSplit && boxActive() && S.selMode) { hit = hitBox(x, y); kind = hit === 'move' ? 'box-move' : hit ? 'box-resize' : 'box-new'; }
  S.drag = { x, y, sx: x, sy: y, split: nearSplit, moved: false, kind, hit, orig: S.sel && normSel(S.sel) }; canvas.setPointerCapture(e.pointerId); canvas.classList.add('dragging');
});
canvas.addEventListener('pointermove', e => {
  const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  if (!S.drag) { // cursor tells the truth about what a press will do
    if (!S.view) return;
    const overSplit = S.site === 'katarapko' && S.mode === 'compare' && Math.abs(x - r.width * S.split) < 14;
    const overPoint = !overSplit && S.points && pointsList().some(p => { const [c, rr] = pxOf(p.x, p.y), [px, py] = toScreen(c, rr); return Math.hypot(px - x, py - y) <= 9; });
    canvas.classList.toggle('over-split', overSplit); canvas.classList.toggle('over-point', overPoint);
    canvas.classList.toggle('over-box', !overSplit && S.selMode && boxActive() && !!hitBox(x, y)); return;
  }
  if (Math.hypot(x - S.drag.sx, y - S.drag.sy) > 3) S.drag.moved = true;
  if (S.drag.split) { S.split = Math.min(.98, Math.max(.02, x / r.width)); $('split-range').value = Math.round(S.split * 100); }
  else if (S.drag.kind) { if (S.drag.moved) dragBox(x, y); }
  else { S.view.tx += x - S.drag.x; S.view.ty += y - S.drag.y; }
  S.drag.x = x; S.drag.y = y; draw();
});
canvas.addEventListener('pointerup', e => { const d = S.drag; S.drag = null; canvas.classList.remove('dragging'); if (d && !d.moved) inspectAt(d.sx, d.sy); else if (d && d.kind && S.sel) { S.sel = normSel(S.sel); renderArea(true); draw(); } });
canvas.addEventListener('wheel', e => { e.preventDefault(); const r = canvas.getBoundingClientRect(); zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, e.clientX - r.left, e.clientY - r.top); }, { passive: false });
function zoom(f, cx, cy) {
  const r = canvas.getBoundingClientRect(); cx ??= r.width / 2; cy ??= r.height / 2;
  const s2 = Math.min(40, Math.max(.2, S.view.s * f)), k = s2 / S.view.s;
  S.view.tx = cx - (cx - S.view.tx) * k; S.view.ty = cy - (cy - S.view.ty) * k; S.view.s = s2; draw();
}
$('zoom-in').onclick = () => zoom(1.4); $('zoom-out').onclick = () => zoom(1 / 1.4); $('zoom-reset').onclick = () => { fit(); draw(); };
canvas.addEventListener('keydown', e => {
  const step = 40, r = canvas.getBoundingClientRect();
  if (boxActive()) {
    if (e.key === 'b' || e.key === 'B') { if (!S.sel) { const site = S.manifest.sites[S.site], c = site.width / 2, rr = site.height / 2; S.sel = { c0: c - 20, r0: rr - 20, c1: c + 20, r1: rr + 20 }; S.selAuto = false; setSelMode(true); renderArea(true); } else setSelMode(!S.selMode); e.preventDefault(); return; }
    if (e.key === 'Escape' && S.selMode) { setSelMode(false); return; }
    if ((e.key === 'Delete' || e.key === 'Backspace') && S.sel) { S.sel = null; S.selAuto = false; renderArea(true); draw(); e.preventDefault(); return; }
    if (e.shiftKey && S.sel && e.key.startsWith('Arrow')) { keyBox(e); e.preventDefault(); return; }
  }
  const k = { ArrowLeft: [step, 0], ArrowRight: [-step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[e.key];
  if (k) { S.view.tx += k[0]; S.view.ty += k[1]; draw(); e.preventDefault(); }
  else if (e.key === '+' || e.key === '=') { zoom(1.3); e.preventDefault(); }
  else if (e.key === '-') { zoom(1 / 1.3); e.preventDefault(); }
  else if (e.key === '0') { fit(); draw(); }
  else if (e.key === 'Enter') { inspectAt(r.width / 2, r.height / 2); }
});
$('split-range').addEventListener('input', e => { S.split = e.target.value / 100; draw(); });
$('before-sel').addEventListener('change', e => { S.before = +e.target.value; if (S.before === S.after) S.after = (S.before + 1) % 3; update(); });
$('after-sel').addEventListener('change', e => { S.after = +e.target.value; if (S.before === S.after) S.before = (S.after + 2) % 3; update(); });
$('points-toggle').addEventListener('change', e => { S.points = e.target.checked; draw(); });
new ResizeObserver(() => { if (S.manifest && !$('view-explore').hidden) { if (!S.view) fit(); draw(); } }).observe($('canvas-wrap'));

/* ---------- evidence ---------- */
const pairLabel = p => dshort(p.split('>')[0]) + '–' + dshort(p.split('>')[1]);
function renderEvidence() {
  const a = S.cases.everglades_e15, red = a.relative_rmse_reduction_percent, ci = a.gauge_boot95_mean_abs_improvement_cm;
  // The interval sits next to the point estimate, not further down the page.
  $('result-lead').textContent = `In this exploratory test, adding NISAR phase lowered the pooled error at ${a.n_folds} withheld gauges from ${fmt(a.pooled_rmse_cm.multiquadric_strongest_baseline)} cm to ${fmt(a.pooled_rmse_cm.nisar)} cm (about ${Math.round(red)}% lower). The gauge-level 95% interval of the improvement, ${ci.map(v => fmt(v, 2)).join(' to ')} cm, includes zero.`;
  $('metrics').innerHTML = `<caption>Table 1. Pooled RMSE, ${a.pairs_scored.length} ascending pairs (track 47), Aug–Oct 2026, gauge-calibrated</caption>
    <thead><tr><th scope="col">Method</th><th scope="col" class="num">RMSE (cm)</th></tr></thead>
    <tbody><tr><td>NISAR-assisted (gauge-calibrated)</td><td class="num">${fmt(a.pooled_rmse_cm.nisar)}</td></tr>
    <tr><td>Best gauge-only baseline (RBF)</td><td class="num">${fmt(a.pooled_rmse_cm.multiquadric_strongest_baseline)}</td></tr></tbody>`;
  const pairs = a.pairs_scored; let sel = 'all';
  const drawAll = () => { seg($('pair-seg'), [['all', 'All'], ...pairs.map(p => [p, pairLabel(p)])], sel, v => { sel = v; drawAll(); }); scatter(sel); table(sel); };
  drawAll(); bars();
  const pc = Object.entries(a.shuffled_phase_control);
  $('placebo').textContent = `When the radar phase values were shuffled among gauges (1,000 times per pair), the improvement disappeared: average shuffled error ${pc.map(([k, v]) => fmt(v.placebo_mean_rmse_cm, 1)).join(', ')} cm versus ${pc.map(([k]) => fmt(a.per_pair_rmse_cm[k].nisar, 1)).join(', ')} cm with the real phase.`;
  $('replication').textContent = 'The same test on the descending orbit (track 170) could not be scored: no pair had eight coherent, eligible gauges. The result is therefore single-geometry and not yet replicated.';
  $('baseline-note').textContent = 'The comparison is against the strongest gauge-only interpolation we tested (a radial-basis function fitted to the other gauges). It is not the operational USGS EDEN water-surface product, which we did not compare against.';
  $('limits').innerHTML = [
    'Three radar pairs, one orbit geometry, one marsh subarea, August–October 2026.',
    `Confidence intervals do not establish a general improvement: the gauge-level 95% interval of the error reduction is ${ci.map(v => fmt(v, 2)).join(' to ')} cm and includes zero.`,
    'Radar phase is referenced and its sign set by the training gauges, so it is a gauge-calibrated estimate, not a stand-alone retrieval.',
    'Daily-mean gauge stage is compared with a morning satellite pass; the NISAR product is provisional.',
    'No oxygen, discharge, residence-time or ecological-risk result follows from this test.'
  ].map(x => `<li>${esc(x)}</li>`).join('');
}
function scatter(sel) {
  const a = S.cases.everglades_e15, rows = a.rows.filter(r => sel === 'all' || r.pair === sel), svg = $('scatter'), out = $('tip');
  const W = 640, H = 440, L = 52, T = 12, R = 12, B = 46; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.replaceChildren();
  const all = a.rows.flatMap(r => [r.observed_cm, r.nisar_cm, r.multiquadric_cm]), lo = Math.floor(Math.min(...all) / 4) * 4, hi = Math.ceil(Math.max(...all) / 4) * 4;
  const X = v => L + (v - lo) / (hi - lo) * (W - L - R), Y = v => T + (H - T - B) - (v - lo) / (hi - lo) * (H - T - B);
  const ax = el('g', { class: 'axis' });
  for (let v = lo; v <= hi; v += 4) { ax.append(el('line', { x1: X(v), x2: X(v), y1: Y(lo), y2: Y(lo) + 4 }), el('text', { x: X(v), y: Y(lo) + 18, 'text-anchor': 'middle' }, v), el('line', { x1: L - 4, x2: L, y1: Y(v), y2: Y(v) }), el('text', { x: L - 8, y: Y(v) + 4, 'text-anchor': 'end' }, v)); }
  ax.append(el('line', { x1: L, x2: W - R, y1: Y(lo), y2: Y(lo) }), el('line', { x1: L, x2: L, y1: T, y2: Y(lo) }));
  svg.append(ax, el('line', { class: 'ref', x1: X(lo), y1: Y(lo), x2: X(hi), y2: Y(hi) }),
    el('text', { x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle' }, 'Measured 12-day water-level change at the withheld gauge (cm)'),
    el('text', { x: 14, y: (T + H - B) / 2, transform: `rotate(-90 14 ${(T + H - B) / 2})`, 'text-anchor': 'middle' }, 'Estimated change (cm)'));
  for (const r of rows) {
    const text = `${r.gauge}, ${pairLabel(r.pair)}: measured ${fmt(r.observed_cm, 1)} cm; NISAR-assisted ${fmt(r.nisar_cm, 1)}; gauge-only ${fmt(r.multiquadric_cm, 1)}`;
    // a thin line joins each gauge's two estimates, so the closer one is visible at a glance
    const g = el('g', { class: 'hit', tabindex: 0 });
    g.append(el('title', {}, text),
      el('line', { class: 'link', x1: X(r.observed_cm), x2: X(r.observed_cm), y1: Y(r.multiquadric_cm), y2: Y(r.nisar_cm) }),
      el('rect', { x: X(r.observed_cm) - 3.5, y: Y(r.multiquadric_cm) - 3.5, width: 7, height: 7, fill: 'var(--base)' }),
      el('circle', { cx: X(r.observed_cm), cy: Y(r.nisar_cm), r: 4.5, fill: 'var(--nisar)' }));
    for (const ev of ['mouseenter', 'focus', 'click']) g.addEventListener(ev, () => { out.textContent = text; });
    svg.append(g);
  }
  out.textContent = 'Hover over or tap a gauge for its values.';
  $('scatter-desc').textContent = `Each vertical pair of marks is one withheld gauge (${rows.length} shown). Marks closer to the dashed line are closer to what the gauge measured. Measured change comes from EDEN gauge observations, not from EDEN model surfaces.`;
}
function bars() {
  const a = S.cases.everglades_e15, svg = $('bars');
  const items = a.pairs_scored.map(p => [pairLabel(p), a.per_pair_rmse_cm[p].nisar, a.per_pair_rmse_cm[p].multiquadric]).concat([['All pairs', a.pooled_rmse_cm.nisar, a.pooled_rmse_cm.multiquadric_strongest_baseline]]);
  const W = 360, rowH = 64, H = items.length * rowH + 28, L = 8, mx = 5; svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.replaceChildren();
  const X = v => L + v / mx * (W - L - 64);
  for (let v = 0; v <= mx; v++) svg.append(el('line', { x1: X(v), x2: X(v), y1: 0, y2: H - 22, stroke: '#ebebeb' }), el('text', { x: X(v), y: H - 6, 'text-anchor': 'middle' }, v));
  items.forEach(([lab, n, b], i) => {
    const y = 4 + i * rowH;
    svg.append(el('text', { x: L, y: y + 12, style: i === items.length - 1 ? 'font-weight:600;fill:#111' : 'fill:#111' }, lab),
      el('rect', { x: L, y: y + 18, width: X(n) - L, height: 16, fill: 'var(--nisar)' }), el('text', { x: X(n) + 6, y: y + 31 }, fmt(n)),
      el('rect', { x: L, y: y + 36, width: X(b) - L, height: 16, fill: 'var(--base)' }), el('text', { x: X(b) + 6, y: y + 49 }, fmt(b)));
  });
  $('bars-desc').textContent = 'Root-mean-square error at withheld gauges, cm (lower is better). Upper bar, blue: NISAR-assisted. Lower bar, orange: gauge-only baseline.';
}
function table(sel) {
  $('rows').innerHTML = S.cases.everglades_e15.rows.filter(r => sel === 'all' || r.pair === sel).map(r => `<tr><td>${esc(pairLabel(r.pair))}</td><td>${esc(r.gauge)}</td><td class="num">${fmt(r.observed_cm)}</td><td class="num">${fmt(r.nisar_cm)}</td><td class="num">${fmt(r.multiquadric_cm)}</td></tr>`).join('');
}

/* ---------- context (Louisiana, measured) ---------- */
function renderContext() {
  const b = S.cases.maurepas_low_oxygen, pr = b.profiles, low = pr.reduce((m, p) => p.do_min_mg_l < m.do_min_mg_l ? p : m);
  const below2 = new Set(pr.filter(p => p.do_min_mg_l < 2 && p.time_local.startsWith('2026-06-01')).map(p => p.station));
  $('ctx-metrics').textContent = `Lowest reading ${fmt(low.do_min_mg_l)} mg/L at ${low.station}, ${dlong(low.time_local.slice(0, 10))}. ${below2.size} of ${new Set(pr.map(p => p.station)).size} stations read below 2 mg/L on 1 June 2026 (${pr.length} field profiles, monthly daytime visits, January–June).`;
  const grid = $('stations'); grid.replaceChildren();
  for (const st of [...new Set(pr.map(p => p.station))]) {
    const ps = pr.filter(p => p.station === st), art = document.createElement('article'); art.className = 'station';
    art.innerHTML = `<h3>${esc(st)} <span>${fmt(Math.abs(ps[0].lat), 3)}° N, ${fmt(Math.abs(ps[0].lon), 3)}° W</span></h3>`;
    const W = 320, H = 170, L = 30, B = 26, T = 8, svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `Dissolved oxygen ranges measured at ${st}, January to June 2026` });
    const Y = v => T + (H - T - B) - v / 12 * (H - T - B), X = i => L + 18 + i * ((W - L - 36) / 5);
    for (let v = 0; v <= 12; v += 4) svg.append(el('line', { x1: L, x2: W, y1: Y(v), y2: Y(v), stroke: '#ebebeb' }), el('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end' }, v));
    // threshold band: neutral fill; the label sits inside the band, left of the first visit, so it never covers a bar
    svg.append(el('rect', { x: L, y: Y(2), width: W - L, height: Y(0) - Y(2), fill: '#f2f2f2' }), el('line', { x1: L, x2: W, y1: Y(2), y2: Y(2), stroke: '#9b1c31', 'stroke-dasharray': '3 3' }),
      el('text', { x: L + 3, y: Y(0) - 4, style: 'fill:#9b1c31;font-size:10px' }, '<2'));
    ps.forEach((p, i) => {
      const g = el('g'); g.append(el('title', {}, `${dlong(p.time_local.slice(0, 10))} ${p.time_local.slice(11, 16)} CST: ${p.do_min_mg_l}–${p.do_max_mg_l} mg/L over ${p.n_depths} depths${p.temperature_c ? `, water ${p.temperature_c[0]}–${p.temperature_c[1]} °C` : ''}`));
      const y1 = Y(p.do_min_mg_l), y2 = Math.min(Y(p.do_max_mg_l), y1 - 3); // keep single-depth visits visible
      g.append(el('line', { x1: X(i), x2: X(i), y1, y2, stroke: p.do_min_mg_l < 2 ? '#9b1c31' : '#111', 'stroke-width': 4 }));
      g.append(el('text', { x: X(i), y: H - 8, 'text-anchor': 'middle' }, MONTHS[+p.time_local.slice(5, 7) - 1]));
      svg.append(g);
    });
    const wrap = document.createElement('div'); wrap.className = 'chart'; wrap.append(svg); art.append(wrap);
    const t = document.createElement('p'); t.className = 'small muted';
    const last = ps[ps.length - 1];
    t.textContent = `1 June: ${last.do_min_mg_l}–${last.do_max_mg_l} mg/L; water ${last.temperature_c ? last.temperature_c.join('–') + ' °C' : 'temperature not recorded'}.`;
    const d = document.createElement('details'); d.className = 'prov';
    d.innerHTML = `<summary>All visits</summary><table><tbody>${ps.map(p => `<tr><td>${dlong(p.time_local.slice(0, 10))}</td><td class="num">${p.do_min_mg_l}–${p.do_max_mg_l} mg/L</td></tr>`).join('')}</tbody></table>`;
    art.append(t, d); grid.append(art);
  }
  $('ctx-limits').innerHTML = [
    'Each bar is one visit: the range of dissolved oxygen across the depths measured that day (field probe). Visits are monthly and in daytime; nothing is drawn between them because nothing was measured between them. Hover over a bar for its exact values.',
    'Source: Louisiana CPRA CIMS discrete water-quality profiles, stations SWMP0201–SWMP0205, 2026. Times are as reported (CST).',
    'These readings do not show how long low oxygen lasted, what caused it, or any effect on fish.',
    b.no_causal_link
  ].map(x => `<li>${esc(x)}</li>`).join('');
}

/* ---------- about ---------- */
function renderAbout() {
  // [name, provider, [[link text, url], ...]]; every link checked to resolve
  const link = ([t, u]) => `<a href="${esc(u)}" target="_blank" rel="noreferrer">${esc(t)}</a>`;
  $('sources').innerHTML = [
    ['NASA/ISRO NISAR L2 GCOV and GUNW (provisional P05023)', 'NASA Alaska Satellite Facility DAAC · open data', [['NISAR data documentation', 'https://nisar-docs.asf.alaska.edu/'], ['ASF data search', 'https://search.asf.alaska.edu/']]],
    ['USGS Everglades Depth Estimation Network (EDEN) gauge coordinates and observed gauge water levels', 'USGS / SFWMD', [['EDEN', 'https://sofia.usgs.gov/eden/'], ['Gauge dataset (doi:10.5066/P13BBYUJ)', 'https://doi.org/10.5066/P13BBYUJ']]],
    ['Louisiana CPRA CIMS discrete water-quality profiles', 'Coastal Protection and Restoration Authority', [['CIMS data portal', 'https://cims.coastal.la.gov/']]],
    ['South Australia water-quality and level records (Katarapko–Pike)', 'Department for Environment and Water', [['Water Data SA', 'https://water.data.sa.gov.au/']]],
  ].map(([a, b, links]) => `<li>${esc(a)}<br><span class="muted small">${esc(b)}</span><br><span class="small">${links.map(link).join(' · ')}</span></li>`).join('');
  if (S.ablation) { const arms = S.ablation.arms || []; const same = arms.every(x => x.max_absolute_numeric_output_difference_from_A === 0);
    $('ablation').innerHTML = `Remove-the-satellite test: with field data only, with conventional satellites added, and with NISAR added, the educational oxygen model produced ${same ? '<strong>identical outputs</strong>' : 'different outputs'} (${arms.length} arms, result hash ${esc((arms[0] || {}).result_sha256 || '').slice(0, 12)}…). NISAR currently constrains no oxygen-model parameter there.`; }
}

/* ---------- routing ---------- */
function route() {
  const v = (location.hash || '#explore').slice(1), view = ['explore', 'evidence', 'context', 'about'].includes(v) ? v : 'explore';
  for (const s of ['explore', 'evidence', 'context', 'about']) $('view-' + s).hidden = s !== view;
  window.scrollTo(0, 0);
  document.querySelectorAll('.tabs a').forEach(a => a.dataset.view === view ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
  document.title = { explore: 'O2tracker: NISAR radar viewer', evidence: 'O2tracker: Everglades test (E15)', context: 'O2tracker: Louisiana oxygen data', about: 'O2tracker: Methods and sources' }[view];
  if (view === 'explore' && S.manifest) { requestAnimationFrame(() => { if (!S.view) fit(); draw(); }); }
}
window.addEventListener('hashchange', route);

(async function init() {
  route();
  try {
    const [m, c, sel] = await Promise.all([json('/data/derived/viewer/manifest.json'), json('/api/case-studies'), json('/data/provenance/selected.json')]);
    S.manifest = m; S.cases = c; S.archive = [...new Set(sel.map(x => x.start.slice(0, 10)))].sort();
    S.ablation = await json('/api/ablation').catch(() => null);
    renderEvidence(); renderContext(); renderAbout(); await update(); route();
  } catch (e) { $('map-loading').hidden = true; $('map-error').hidden = false; $('map-error').textContent = 'Data could not be loaded: ' + e.message; }
})();
})();
