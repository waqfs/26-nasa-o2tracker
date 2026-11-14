"""Build the O2tracker observation-viewer assets from retained NISAR rasters (deterministic).

Usage (run from public-repo with the project virtual environment):
  python scripts/build_viewer_assets.py --katarapko-raw <dir with NISAR_L2_PR_GCOV_* folders> \
      --everglades-dir <dir holding e14_jobs.json, raw/, e15/>

Outputs data/derived/viewer/*.png (8-bit value-encoded rasters, NOT colour images) and
data/derived/viewer/manifest.json with exact geotransforms, encodings and source SHA-256.
Decoding: value = offset + code * scale for code >= 1; code 0 = no data.
"""
import argparse, csv, hashlib, json, pathlib
import numpy as np, rasterio
from PIL import Image
from pyproj import Transformer

ap = argparse.ArgumentParser()
ap.add_argument('--katarapko-raw', required=True)
ap.add_argument('--everglades-dir', required=True)
ap.add_argument('--out', default='data/derived/viewer')
a = ap.parse_args()
OUT = pathlib.Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def encode(values, valid, lo, hi, name):
    """Quantise to 1..251 (250 steps between lo and hi), 0 = no data. Returns encoding metadata."""
    scale = (hi - lo) / 250.0
    code = np.zeros(values.shape, np.uint8)
    v = np.clip(values, lo, hi)
    code[valid] = (np.round((v[valid] - lo) / scale) + 1).astype(np.uint8)
    Image.fromarray(code, mode='L').save(OUT / name, optimize=True)
    return {'file': name, 'offset': lo - scale, 'scale': scale, 'nodata_code': 0, 'clip': [lo, hi],
            'png_sha256': sha(OUT / name), 'valid_fraction': float(valid.mean())}


def block_mean(arr, valid, f):
    h, w = (arr.shape[0] // f) * f, (arr.shape[1] // f) * f
    x = np.where(valid, arr, 0.0)[:h, :w].reshape(h // f, f, w // f, f)
    n = valid[:h, :w].reshape(h // f, f, w // f, f).sum(axis=(1, 3))
    s = x.sum(axis=(1, 3))
    with np.errstate(invalid='ignore', divide='ignore'):
        m = s / n
    return m, n >= (f * f) // 2 + 1


manifest = {'schema': 'o2tracker/viewer/1', 'encoding_note': 'value = offset + code*scale for code>=1; code 0 = no data. Values are quantised for display; sampled values are approximate to +/- scale/2.', 'sites': {}}

# ---------------- Katarapko-Pike: GCOV backscatter, three acquisitions on one identical grid ----------------
F = 2  # 20 m native -> 40 m display (power averaged, mask-aware)
kat = pathlib.Path(a.katarapko_raw)
acq = []
grid = None
for g in sorted(kat.glob('NISAR_L2_PR_GCOV_*')):
    files = {d.name: next(d.glob('*.tif')) for d in g.iterdir() if d.is_dir() and any(d.glob('*.tif'))}
    if not {'HHHH', 'HVHV', 'mask'} <= set(files):
        continue
    with rasterio.open(files['mask']) as m:
        valid = m.read(1) == 1
        t, crs, W, H = m.transform, m.crs, m.width, m.height
    this_grid = (str(crs), tuple(round(x, 6) for x in t[:6]), W, H)
    grid = grid or this_grid
    assert this_grid == grid, 'GCOV grids differ; before/after comparison not allowed'
    date = g.name.split('_')[11][:8]
    item = {'granule_id': g.name, 'date': f'{date[:4]}-{date[4:6]}-{date[6:]}', 'time_utc': g.name.split('_')[11][9:15], 'layers': {}, 'source_sha256': {}}
    for pol in ('HHHH', 'HVHV'):
        with rasterio.open(files[pol]) as s:
            p = s.read(1).astype('float64')
        ok = valid & np.isfinite(p) & (p > 0)
        mp, mv = block_mean(p, ok, F)
        db = 10 * np.log10(np.where(mv, mp, np.nan))
        lo, hi = (-30.0, 0.0) if pol == 'HHHH' else (-38.0, -8.0)
        item['layers'][pol[:2]] = encode(db, mv & np.isfinite(db), lo, hi, f"katarapko_{date}_{pol[:2]}.png")
        item['source_sha256'][pol] = sha(files[pol])
    item['source_sha256']['mask'] = sha(files['mask'])
    acq.append(item)
tt = grid[1]
tr = Transformer.from_crs('EPSG:4326', grid[0], always_xy=True)
stations = json.loads(pathlib.Path('data/derived/stations.json').read_text(encoding='utf-8'))['stations']
pts = []
for s in stations:
    x, y = tr.transform(s['longitude'], s['latitude'])
    pts.append({'id': s['id'], 'name': s['name'], 'x': x, 'y': y, 'lon': s['longitude'], 'lat': s['latitude'], 'kind': 'River oxygen station (independent sensor)'})
manifest['sites']['katarapko'] = {
    'name': 'Katarapko–Pike floodplain, South Australia', 'product': 'NISAR L2 GCOV (provisional P05023, product 1.0.11)', 'track_frame': 'Track 153 ascending, frame 160',
    'quantity': 'Radar backscatter (gamma-naught power, dB)', 'status': 'OBSERVED', 'crs': grid[0], 'epsg': int(grid[0].split(':')[1]), 'utm_zone': 54, 'south': True,
    'transform': [tt[0] * F, 0, tt[2], 0, tt[4] * F, tt[5]], 'width': grid[2] // F, 'height': grid[3] // F, 'native_resolution_m': abs(tt[0]), 'display_resolution_m': abs(tt[0]) * F,
    'processing': 'Mask-aware 2x2 block mean of linear power (mask code 1 = valid), then 10*log10; same grid for all dates (identical CRS/transform verified).',
    'comparability': {'same_track_frame': True, 'same_mode': '20+5 MHz dual-pol HH/HV', 'same_grid': True, 'registration_check': 'integer-pixel normalized correlation found 0 px offset in all windows (radar_audit.json)', 'allowed': True,
                      'caveats': ['Provisional product; possible radiometric residuals', 'A backscatter change is not by itself a flooding change', 'Regional reference targets also changed between dates (see radar_audit.json)']},
    'acquisitions': acq, 'points': pts}

# ---------------- Everglades WCA-3A: GUNW coherence and unwrapped phase for eight 12-day pairs ----------------
ev = pathlib.Path(a.everglades_dir)
jobs = json.loads((ev / 'e14_jobs.json').read_text())
P = {}
for k, v in jobs.items():
    P.setdefault(v['concept_id'], {'t1': v['time'], 't2': v['secondary_time'], 'gid': v['granule_id']})[v['layer']] = ev / v['raster']['file']
gauges = {r['eden']: r for r in csv.DictReader(open(ev / 'e15' / 'e15_gauges.csv'))}
feats = list(csv.DictReader(open(ev / 'e15' / 'e15_features_flagged.csv')))
preds = {(r['pair'], r['gauge']): r for r in csv.DictReader(open(ev / 'e15' / 'e15_predictions.csv'))}
pairs = []; egrid = None
for cid, d in sorted(P.items(), key=lambda kv: kv[1]['t1']):
    with rasterio.open(d['coherenceMagnitude']) as s:
        coh = s.read(1).astype('float64'); t = s.transform; crs = s.crs; W, H = s.width, s.height
    with rasterio.open(d['unwrappedPhase']) as s:
        ph = s.read(1).astype('float64')
    with rasterio.open(d['connectedComponents']) as s:
        cc = s.read(1)
    this = (str(crs), tuple(round(x, 6) for x in t[:6]), W, H); egrid = egrid or this; assert this == egrid
    d1, d2 = d['t1'][:10], d['t2'][:10]
    okc = np.isfinite(coh) & (coh > 0)
    okp = np.isfinite(ph) & (cc > 0)
    ph_rel = ph - np.median(ph[okp]) if okp.any() else ph
    lp = encode(ph_rel, okp, -12.0, 12.0, f'everglades_{d1}_{d2}_phase.png')
    lp['reference'] = 'scene median of unwrapped phase over pixels with a nonzero connected component'
    key = f'{d1}>{d2}'
    g_out = []
    for f in feats:
        if f['d1'] != d1 or f['eden'] not in gauges:
            continue
        g = gauges[f['eden']]
        s1, s2 = f['s1'], f['s2']
        obs = (float(s2) - float(s1)) * 30.48 if s1 and s2 else None
        pr = preds.get((key, f['eden']))
        g_out.append({'id': f['eden'], 'agency': g['agency'], 'vegetation': g['veg'], 'x': float(g['UTM_easting']), 'y': float(g['UTM_northing']),
                      'lon': float(g['Longitude']), 'lat': float(g['Latitude']), 'coherence_3x3': round(float(f['coh']), 3), 'component': int(f['cc']),
                      'observed_change_cm': None if obs is None else round(obs, 2), 'eligible_e15': f['elig'] == 'True',
                      'scored_e15': pr is not None, 'nisar_estimate_cm': None if pr is None else round(float(pr['nisar']), 2),
                      'baseline_estimate_cm': None if pr is None else round(float(pr['B4']), 2)})
    pairs.append({'concept_id': cid, 'granule_id': d['gid'], 'reference_date': d1, 'secondary_date': d2, 'interval_days': 12,
                  'layers': {'coherence': encode(coh, okc, 0.0, 1.0, f'everglades_{d1}_{d2}_coherence.png'), 'phase': lp},
                  'median_coherence': float(np.median(coh[okc])), 'scored_in_e15': any(x['scored_e15'] for x in g_out), 'gauges': g_out,
                  'source_sha256': {n: sha(d[n]) for n in ('coherenceMagnitude', 'unwrappedPhase', 'connectedComponents')}})
with_obs = {g['id'] for p in pairs for g in p['gauges'] if g['observed_change_cm'] is not None}
for p in pairs:  # drop gauges with no 2026 observed stage at all (duplicate legacy identities 3ANW/3ANE)
    p['gauges'] = [g for g in p['gauges'] if g['id'] in with_obs]
manifest['sites']['everglades'] = {
    'name': 'Everglades Water Conservation Area 3A, Florida', 'product': 'NISAR L2 GUNW (provisional P05023, product 1.0.11), HH, 20 MHz', 'track_frame': 'Track 47 ascending, frame 15',
    'quantity': 'Interferometric coherence (0–1) and unwrapped phase (radians, relative to scene median) between two passes 12 days apart', 'status': 'OBSERVED (coherence, phase) · DERIVED (gauge estimates)',
    'crs': egrid[0], 'epsg': int(egrid[0].split(':')[1]), 'utm_zone': 17, 'south': False, 'transform': list(egrid[1]), 'width': egrid[2], 'height': egrid[3],
    'native_resolution_m': abs(egrid[1][0]), 'display_resolution_m': abs(egrid[1][0]),
    'processing': 'Harmony GeoTIFF subsets of the GUNW product; no resampling. Phase masked where connected component is 0 and shown relative to the scene median; no ionosphere, troposphere or tide correction applied.',
    'phase_to_los_note': 'At L-band (~0.238 m wavelength) one 2π cycle of phase corresponds to ~11.9 cm of line-of-sight path change; phase is not converted to water level here.',
    'pairs': pairs}
manifest['generated_from'] = 'scripts/build_viewer_assets.py'
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1))
print('katarapko acquisitions', len(acq), 'everglades pairs', len(pairs), 'files', len(list(OUT.glob('*.png'))))
