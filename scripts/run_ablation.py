"""Frozen A/B/C evidence ablation: do not change parameters, dates, fitting or selected population."""
import json
from dataclasses import asdict, replace
from oxygen_debt.flood_context import context
from oxygen_debt.flood import FloodExperiment, experiment
from oxygen_debt.essentiality import ARMS,digest,numeric_delta,dossier
from oxygen_debt.settings import SNAPSHOT_ROOT

configuration=FloodExperiment()
records=[];baseline=None
for arm,name in ARMS.items():
    evidence=dossier(arm=arm)
    result=experiment(configuration)  # Independent rerun, not a copy of the prior arm's outputs.
    if baseline is None:baseline=result
    delta=numeric_delta(baseline,result)
    records.append(dict(arm=arm,name=name,result_sha256=digest(result),bounds_sha256=digest(result['bounds']),
                        max_absolute_numeric_output_difference_from_A=delta,
                        potential_oxygen_demand_kg=result['potential_oxygen_demand_kg'],minimum_river_oxygen_mg_l=result['minimum_river_oxygen_mg_l'],
                        added_observables=['Independent field/water-quality records']+(['Landsat exposed-water labels','Sentinel-1 VV/VH','Sentinel-2 labels'] if arm in ['B','C'] else [])+(['NISAR HH/HV power and change','L-band reference-offset sensitivity'] if arm=='C' else []),
                        nisar_constrained_parameters=evidence['constrained_oxygen_parameters'],flood_constraint=evidence['quantitative_flood_constraint'],
                        decision='Same unmet need for verified inundation, local routing/flow and carbon measurements. C additionally exposes an L-band surface-change/calibration question; no decision outcome evaluated.'))
result=dict(protocol='Frozen before execution: docs/NISAR_ESSENTIALITY.md',configuration=asdict(configuration),
            fixed_location='candidate-2',fixed_anchor_utc=dossier()['fixed_anchor_utc'],arms=records,
            result='EXACTLY IDENTICAL oxygen model outputs in A/B/C' if len({r['result_sha256'] for r in records})==1 else 'DIFFERENCE REQUIRES INVESTIGATION',
            scope='Structural input ablation of the current implementation, not accuracy validation, causal inference or a test of all possible NISAR methods.',
            spatial_selection_caution=dossier()['selection_caution'],
            strongest_contribution='NISAR adds measured L-band changes for questioning physical explanations; it supplies no validated quantitative environmental constraint in this case.',
            reference_sensitivity=dossier()['diagnostic'],measurement_requirements=dossier()['measurement_plan'])
# Secondary dependency control: specified after the primary run; first retained
# Pike epoch with GOOD aligned upstream O2 and temperature. No target fitting.
boundary=context('A4261053','candidate-2',0)['boundary_inputs']
if any(boundary[k]['observation'] is None for k in ['oxygen','temperature']):raise ValueError('Expected quality-eligible fixed upstream control')
control_config=replace(configuration,upstream_oxygen_mg_l=boundary['oxygen']['observation']['value'],temperature_c=boundary['temperature']['observation']['value'])
control=[];first=None
for arm in ARMS:
    current=experiment(control_config)
    if first is None:first=current
    control.append(dict(arm=arm,result_sha256=digest(current),max_absolute_numeric_output_difference_from_A=numeric_delta(first,current),potential_oxygen_demand_kg=current['potential_oxygen_demand_kg'],minimum_river_oxygen_mg_l=current['minimum_river_oxygen_mg_l']))
result['matched_upstream_control']=dict(configuration=asdict(control_config),station='A4261053',fixed_location='candidate-2',fixed_anchor_utc=dossier(pass_index=0)['fixed_anchor_utc'],boundary_inputs=boundary,arms=control,
    scope='Secondary software-dependency control specified after the primary run. GOOD upstream data are constant assumed boundaries, not proof of connection to the selected block/target. No new calibration, label search or target fit.')
(SNAPSHOT_ROOT/'derived/nisar_ablation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result['result']);print([(r['arm'],r['max_absolute_numeric_output_difference_from_A'],r['result_sha256']) for r in records])
