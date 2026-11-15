/* O2tracker landing experiment. Uses the same real, value-encoded NISAR rasters as the explorer
   (data/derived/viewer) and the E15 numbers from /api/case-studies. Nothing here is synthesised. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const dshort = iso => { const [, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]}`; };
const dB = v => v === null ? 'no data' : (v < 0 ? '−' : '') + Math.abs(v).toFixed(1) + ' dB';
const dBsigned = v => (v < 0 ? '−' : '+') + Math.abs(v).toFixed(1) + ' dB';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const decode = (enc, code) => code === 0 ? null : enc.offset + code * enc.scale;

const GRAY = [-25, -3];       // same display range as the explorer
const DIFF = 6;               // ±dB for the change view
const S = { w: 0, h: 0, enc: null, codes: null, imgs: null, mode: 'compare', split: .5, hover: null, pin: null, drag: false, touched: false, dates: [], start: null };
const cv = $('cv'), ctx = cv.getContext('2d');

function rasterOf(file) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => { const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0);
      const d = x.getImageData(0, 0, img.width, img.height).data, codes = new Uint8Array(img.width * img.height); for (let i = 0; i < codes.length; i++) codes[i] = d[i * 4]; res({ w: img.width, h: img.height, codes }); };
    img.onerror = () => rej(new Error('Could not load ' + file)); img.src = '/data/derived/viewer/' + file;
  });
}
const gray = t => { const g = 12 + 238 * t; return [g, g, g * .99]; };
const diverge = t => { // blue (decrease) - white - orange (increase), as in the explorer
  const a = t < .5 ? [33, 102, 172] : [247, 247, 247], b = t < .5 ? [247, 247, 247] : [178, 88, 24], u = t < .5 ? t * 2 : (t - .5) * 2;
  return [0, 1, 2].map(i => a[i] + (b[i] - a[i]) * u);
};
function paint(valueAt, lo, hi, color) {
  const { w, h } = S, c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d'), im = x.createImageData(w, h), d = im.data;
  for (let i = 0; i < w * h; i++) {
    const v = valueAt(i); if (v === null) { d[i * 4] = 217; d[i * 4 + 1] = 220; d[i * 4 + 2] = 225; d[i * 4 + 3] = 255; continue; }
    const rgb = color(Math.max(0, Math.min(1, (v - lo) / (hi - lo))));
    d[i * 4] = rgb[0]; d[i * 4 + 1] = rgb[1]; d[i * 4 + 2] = rgb[2]; d[i * 4 + 3] = 255;
  }
  x.putImageData(im, 0, 0); return c;
}

/* ---------- drawing ---------- */
function size() {
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const W = Math.round(r.width * dpr), H = Math.round(r.height * dpr);
  if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
  return { W: r.width, H: r.height, dpr };
}
function draw() {
  if (!S.imgs) return;
  const { W, H, dpr } = size(); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = true; ctx.clearRect(0, 0, W, H);
  if (S.mode === 'change') ctx.drawImage(S.imgs.diff, 0, 0, W, H);
  else {
    ctx.drawImage(S.imgs.before, 0, 0, W, H);
    const xs = W * S.split; ctx.save(); ctx.beginPath(); ctx.rect(xs, 0, W - xs, H); ctx.clip(); ctx.drawImage(S.imgs.after, 0, 0, W, H); ctx.restore();
    ctx.fillStyle = '#fff'; ctx.fillRect(xs - 1.5, 0, 3, H); ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.fillRect(xs - 2.5, 0, 1, H); ctx.fillRect(xs + 1.5, 0, 1, H);
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#15181c'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.rect(xs - 9, H / 2 - 22, 18, 44); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#15181c'; ctx.beginPath(); ctx.moveTo(xs - 4, H / 2); ctx.lineTo(xs - 1, H / 2 - 4); ctx.lineTo(xs - 1, H / 2 + 4); ctx.fill(); ctx.beginPath(); ctx.moveTo(xs + 4, H / 2); ctx.lineTo(xs + 1, H / 2 - 4); ctx.lineTo(xs + 1, H / 2 + 4); ctx.fill();
  }
  for (const p of [S.pin, S.hover]) if (p) { const x = (p.col + .5) / S.w * W, y = (p.row + .5) / S.h * H; ctx.lineWidth = 3; ctx.strokeStyle = '#fff'; ctx.strokeRect(x - 8, y - 8, 16, 16); ctx.lineWidth = 1.5; ctx.strokeStyle = '#15181c'; ctx.strokeRect(x - 8, y - 8, 16, 16); }
  $('tag-l').hidden = S.mode === 'change'; $('tag-r').hidden = S.mode === 'change';
}

/* ---------- readout ---------- */
function readout() {
  const p = S.hover || S.pin;
  if (!p) { $('r1').textContent = $('r2').textContent = $('r3').textContent = '·'; $('rnote').textContent = 'Hover over the image. Click to pin a spot.'; return; }
  const i = p.row * S.w + p.col, a = decode(S.enc[0], S.codes[0][i]), b = decode(S.enc[1], S.codes[1][i]);
  $('r1').textContent = dB(a); $('r2').textContent = dB(b); $('r3').textContent = a !== null && b !== null ? dBsigned(b - a) : 'no data';
  $('rnote').textContent = (S.hover ? 'Under the pointer' : S.pin === S.start ? 'Starting spot, the largest average change in this scene (8 × 8 pixel block)' : 'Pinned') + ': pixel ' + p.col + ', ' + p.row + '. Hover or click anywhere else. Observed values, decoded from the display raster.';
}
function spot(e) {
  const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  const col = Math.floor(x / r.width * S.w), row = Math.floor(y / r.height * S.h);
  return col < 0 || row < 0 || col >= S.w || row >= S.h ? null : { col, row };
}
const nearSplit = e => { const r = cv.getBoundingClientRect(); return S.mode === 'compare' && Math.abs(e.clientX - r.left - r.width * S.split) < 18; };

/* ---------- interaction ---------- */
cv.addEventListener('pointerdown', e => {
  S.touched = true; $('hint').textContent = 'Drag the line · click to pin';
  if (nearSplit(e)) { S.drag = true; cv.setPointerCapture(e.pointerId); } else { S.pin = spot(e); readout(); draw(); }
});
cv.addEventListener('pointermove', e => {
  cv.classList.toggle('over-split', nearSplit(e) || S.drag);
  if (S.drag) { const r = cv.getBoundingClientRect(); S.split = Math.min(.97, Math.max(.03, (e.clientX - r.left) / r.width)); }
  if (e.pointerType !== 'touch' || S.drag) S.hover = S.drag ? S.hover : spot(e);
  readout(); draw();
});
cv.addEventListener('pointerup', () => { S.drag = false; });
cv.addEventListener('pointerleave', () => { S.hover = null; readout(); draw(); });
cv.addEventListener('keydown', e => {
  S.touched = true;
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { S.split = Math.min(.97, Math.max(.03, S.split + (e.key === 'ArrowRight' ? .04 : -.04))); draw(); e.preventDefault(); }
  else if (e.key === 'Enter') { S.pin = { col: Math.floor(S.w * S.split), row: Math.floor(S.h / 2) }; readout(); draw(); }
});
document.querySelectorAll('.mode button').forEach(b => b.addEventListener('click', () => {
  S.mode = b.dataset.mode; document.querySelectorAll('.mode button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  $('hint').textContent = S.mode === 'change' ? 'Blue: weaker echo · Orange: stronger echo' : 'Drag the line'; draw();
}));
new ResizeObserver(draw).observe($('stage'));

function sweep() { // one gentle sweep on load shows what the control does; stops the moment the visitor touches it
  if (reduced) return; const t0 = performance.now(), from = .96, to = .5, dur = 1700;
  const step = now => { if (S.touched) return; const u = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - u, 3); S.split = from + (to - from) * e; draw(); if (u < 1) requestAnimationFrame(step); };
  S.split = from; draw(); requestAnimationFrame(step);
}

/* ---------- E15 result ---------- */
function result(c) {
  const a = c.everglades_e15, n = a.pooled_rmse_cm.nisar, b = a.pooled_rmse_cm.multiquadric_strongest_baseline, ci = a.gauge_boot95_mean_abs_improvement_cm, red = Math.round(a.relative_rmse_reduction_percent);
  $('big').innerHTML = `${b.toFixed(2)} <span class="arrow">→</span> <span class="to">${n.toFixed(2)}</span><small>cm error</small>`;
  const NS = 'http://www.w3.org/2000/svg', svg = $('dumb'), W = 560, H = 120, L = 8, R = 24, X = v => L + v / 5 * (W - L - R);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.replaceChildren();
  const el = (t, at, txt) => { const e = document.createElementNS(NS, t); for (const k in at) e.setAttribute(k, at[k]); if (txt !== undefined) e.textContent = txt; svg.append(e); };
  for (let v = 0; v <= 5; v++) { el('line', { x1: X(v), x2: X(v), y1: 62, y2: 70, stroke: '#9a9a9a' }); el('text', { x: X(v), y: 88, 'text-anchor': 'middle' }, v); }
  el('line', { x1: X(0), x2: X(5), y1: 66, y2: 66, stroke: '#9a9a9a' });
  el('line', { x1: X(n), x2: X(b), y1: 40, y2: 40, stroke: '#15181c', 'stroke-width': 2 });
  el('circle', { cx: X(b), cy: 40, r: 9, fill: 'var(--ochre)' }); el('circle', { cx: X(n), cy: 40, r: 9, fill: 'var(--teal)' });
  el('text', { x: X(b), y: 18, 'text-anchor': 'middle' }, 'Gauge-only'); el('text', { x: X(n), y: 18, 'text-anchor': 'middle' }, 'With NISAR');
  el('text', { x: (W) / 2, y: 112, 'text-anchor': 'middle' }, 'Error at the hidden gauges (cm). Lower is better.');
  $('dumb-desc').innerHTML = `<strong>About ${red}% lower error</strong> in this one test: Everglades WCA-3A, ${a.pairs_scored.length} radar pairs, ${a.n_folds} hidden gauges. The 95% interval of the improvement (${ci.map(v => v.toFixed(2).replace('-', '−')).join(' to ')} cm) includes zero, and a second orbit could not be scored. Exploratory, not yet replicated.`;
}

(async function init() {
  try {
    const [m, c] = await Promise.all([fetch('/data/derived/viewer/manifest.json').then(r => r.json()), fetch('/api/case-studies').then(r => r.json())]);
    result(c);
    const site = m.sites.katarapko, A = site.acquisitions, enc = [A[0].layers.HH, A[1].layers.HH];
    const rs = await Promise.all(enc.map(e => rasterOf(e.file)));
    S.w = rs[0].w; S.h = rs[0].h; S.enc = enc; S.codes = rs.map(r => r.codes); S.dates = [A[0].date, A[1].date];
    document.documentElement.style.setProperty('--ar', S.w / S.h);
    $('tag-l').textContent = $('r1l').textContent = dshort(S.dates[0]); $('tag-r').textContent = $('r2l').textContent = dshort(S.dates[1]);
    const val = k => i => decode(enc[k], S.codes[k][i]);
    S.imgs = {
      before: paint(val(0), GRAY[0], GRAY[1], gray), after: paint(val(1), GRAY[0], GRAY[1], gray),
      diff: paint(i => { const a = val(0)(i), b = val(1)(i); return a === null || b === null ? null : b - a; }, -DIFF, DIFF, diverge)
    };
    // start pinned on the block with the largest mean change, so the readout shows real numbers from the first second
    let best = null; const B = 8;
    for (let r = 0; r + B <= S.h; r += B) for (let c0 = 0; c0 + B <= S.w; c0 += B) {
      let sum = 0, n = 0; for (let y = 0; y < B; y++) for (let x = 0; x < B; x++) { const i = (r + y) * S.w + c0 + x, a = val(0)(i), b = val(1)(i); if (a !== null && b !== null) { sum += b - a; n++; } }
      if (n === B * B && (!best || Math.abs(sum / n) > Math.abs(best.m))) best = { m: sum / n, col: c0 + B / 2, row: r + B / 2 };
    }
    if (best) { S.start = S.pin = { col: Math.floor(best.col), row: Math.floor(best.row) }; }
    $('loading').hidden = true; readout(); draw(); sweep();
  } catch (e) { $('loading').textContent = 'Radar could not be loaded: ' + e.message; }
})();
})();
