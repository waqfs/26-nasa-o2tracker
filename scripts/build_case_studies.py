"""Build data/derived/case_studies.json from retained private research outputs (not shipped).
Usage: python scripts/build_case_studies.py E15_DIR MAUREPAS_PROFILE_JSON
E15_DIR holds e15_predictions.csv, e15_score.json, e15_audit.json, e15_gauges.csv, e15_gate.json, e15rep_gate.json (rep path via --rep)."""
import csv, json, hashlib, sys, pathlib
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
e15 = pathlib.Path(sys.argv[1]); mau = pathlib.Path(sys.argv[2]); rep = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
score = json.loads((e15/'e15_score.json').read_text()); audit = json.loads((e15/'e15_audit.json').read_text()); gate = json.loads((e15/'e15_gate.json').read_text())
gauges = {r['eden']: r for r in csv.DictReader(open(e15/'e15_gauges.csv'))}
rows = []
for r in csv.DictReader(open(e15/'e15_predictions.csv')):
    g = gauges[r['gauge']]
    rows.append({'pair': r['pair'], 'gauge': r['gauge'], 'agency': g['agency'], 'vegetation': g['veg'], 'lon': round(float(g['Longitude']), 5), 'lat': round(float(g['Latitude']), 5),
                 'observed_cm': round(float(r['truth_cm']), 2), 'nisar_cm': round(float(r['nisar']), 2), 'multiquadric_cm': round(float(r['B4']), 2), 'idw_cm': round(float(r['B2']), 2), 'thin_plate_cm': round(float(r['B3']), 2), 'nearest_cm': round(float(r['B1']), 2)})
prof = json.loads(mau.read_text()); lo = []
for p in prof['profiles']:
    r = p['ranges'].get('Dissolved Oxygen (mg/L)')
    lo.append({'station': p['site'], 'time_local': p['time'], 'lon': p['coordinates'][0], 'lat': p['coordinates'][1], 'do_min_mg_l': r[0], 'do_max_mg_l': r[1], 'depth_ft': p['ranges'].get('Measurement Depth (ft)'), 'n_depths': p['rows'], 'temperature_c': next((v for k, v in p['ranges'].items() if k.startswith('Water Temperature')), None), 'salinity_ppt': p['ranges'].get('Salinity (ppt)')})
out = {
 'schema': 'oxygen-debt/case-studies/1',
 'status': 'EXPERIMENTAL CANDIDATE - not part of release 0.3.0',
 'everglades_e15': {
  'title': 'Everglades WCA-3A: gauge-calibrated NISAR water-level-change estimates (E15)',
  'site': 'Water Conservation Area 3A, Florida, USA', 'product': 'NISAR GUNW provisional P05023 v1.0.11, ascending track 47, frame 15, 12-day pairs',
  'pairs_scored': list(score['info'].keys()), 'n_folds': score['n_folds'], 'method': 'Leave-one-gauge-out. Phase referenced and sign-set only by training gauges in the same coherent component; withheld gauge never used.',
  'truth': 'EDEN observed daily-mean stage change (cm) at USGS/SFWMD marsh gauges (not EDEN model surfaces)',
  'pooled_rmse_cm': {'nisar': round(score['pooled_RMSE_cm']['nisar'], 2), 'multiquadric_strongest_baseline': round(score['pooled_RMSE_cm']['B4'], 2), 'idw': round(score['pooled_RMSE_cm']['B2'], 2), 'thin_plate': round(score['pooled_RMSE_cm']['B3'], 2), 'nearest': round(score['pooled_RMSE_cm']['B1'], 2)},
  'pooled_mae_cm': {'nisar': round(score['pooled_MAE_cm']['nisar'], 2), 'multiquadric_strongest_baseline': round(score['pooled_MAE_cm']['B4'], 2)},
  'relative_rmse_reduction_percent': round(100*(1-score['rmse_ratio_nisar_over_best']), 1),
  'per_pair_rmse_cm': {k: {'nisar': round(v['nisar'], 2), 'multiquadric': round(v['B4'], 2)} for k, v in score['per_pair_RMSE_cm'].items()},
  'pair_cluster_boot95_mean_abs_improvement_cm': [round(x, 2) for x in score['pair_cluster_boot95_mean_abs_improvement_cm']],
  'gauge_boot95_mean_abs_improvement_cm': [round(x, 2) for x in score['gauge_boot95_mean_abs_improvement_cm']],
  'shuffled_phase_control': {k: {'placebo_mean_rmse_cm': round(v['RMSE_placebo_shuffled_phase_mean'], 2), 'fraction_placebo_as_good_as_nisar': v['frac_placebo_below_nisar']} for k, v in audit.items() if '>' in k},
  'eligibility_pairs_passed': gate['n_pairs_pass_E15'], 'eligibility_pairs_total': len(gate['pairs']),
  'replication_descending_stack_170': 'INCONCLUSIVE - usability gate failed (0 of 6 pairs had >= 8 coherent eligible gauges); not scored',
  'frozen_verdict': 'PASS (exploratory, single geometry)', 'rows': rows,
  'limitations': ['Promising, exploratory, single-geometry result; three interferometric pairs; one subarea.', 'Not a fully replicated or operationally validated water-level retrieval.', 'Phase is referenced and sign-set by training gauges; it is a gauge-calibrated estimate, not an absolute retrieval.', 'The multiquadric baseline is a proxy for EDEN-style gauge interpolation, not the operational EDEN system; EDEN surfaces were not used.', 'Does not show improvement over operational EDEN surfaces.', 'Does not demonstrate oxygen prediction, discharge, residence time or ecological risk forecasting.', 'Daily-mean gauge stage is compared with a morning overpass; provisional NISAR product with a possible ~1 dB mode caveat.']},
 'maurepas_low_oxygen': {
  'title': 'Lake Maurepas / Maurepas Swamp, Louisiana: measured dissolved oxygen, 2026',
  'source': 'CPRA CIMS discrete water-quality profiles, stations SWMP0201-SWMP0205, six monthly visits Jan-Jun 2026; values are min-max over the measured depths of each profile',
  'profiles': lo, 'lowest_observed_mg_l': min(p['do_min_mg_l'] for p in lo),
  'statement': 'Measured field-probe snapshots show dissolved oxygen falling to about 1 mg/L at several stations on 1 June 2026. These are monthly daytime profiles; they do not establish a hypoxic event duration, fish stress, a flood cause, or any NISAR relationship.',
  'no_causal_link': 'No causal or predictive NISAR-to-oxygen relationship has been established at Maurepas or anywhere in this project. The Everglades and Maurepas panels use different sites, data and dates.'},
 'provenance': {'e15_predictions_sha256': sha(e15/'e15_predictions.csv'), 'e15_score_sha256': sha(e15/'e15_score.json'), 'maurepas_profile_summary_sha256': sha(mau)}}
pathlib.Path('data/derived/case_studies.json').write_text(json.dumps(out, indent=1))
print('wrote', len(rows), 'rows;', len(lo), 'profiles; lowest DO', out['maurepas_low_oxygen']['lowest_observed_mg_l'])
