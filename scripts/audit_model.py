"""Additional all-member base-ensemble convergence audit, with no model tuning or target fitting."""
import json
import numpy as np
from oxygen_debt.flood import FloodExperiment,parameter_bounds,integrate,RATIO
from oxygen_debt.settings import SNAPSHOT_ROOT,read_json

records=[]
for name,saved in read_json('derived/flood_experiment.json').items():
    config=FloodExperiment(**saved['configuration']);bounds=parameter_bounds(config);names=list(bounds)
    draws=np.random.default_rng(config.seed).random((config.samples*2,len(names)))
    parameters={k:bounds[k][0]+draws[:,i]*(bounds[k][1]-bounds[k][0]) for i,k in enumerate(names)}
    coarse=integrate(parameters,config.days,config.upstream_oxygen_mg_l,dt=saved['numerical_step_days'])
    fine=integrate(parameters,config.days,config.upstream_oxygen_mg_l,dt=saved['numerical_step_days']/2)
    vf=parameters['area_ha']*10000*parameters['depth_m'];qf=vf*parameters['exchange_per_day'];qr=parameters['river_flow_m3_s']*86400;f=parameters['connected_fraction']
    water_error=float(np.max(np.abs((qr+qf)-((qr+f*qf)+(1-f)*qf))))
    carbon_error=float(np.max(np.abs(coarse['carbon_remaining_kg']-(coarse['initial_carbon_kg']+coarse['carbon_boundary_net_kg']-coarse['consumed_oxygen_kg']/RATIO))))
    difference=float(np.max(np.abs(coarse['minimum']-fine['minimum'])))
    records.append(dict(scenario=name,members=len(vf),step_days=saved['numerical_step_days'],half_step_days=saved['numerical_step_days']/2,
                        max_minimum_river_difference_mg_l=difference,maximum_terminal_carbon_inventory_residual_kg=carbon_error,
                        maximum_oxygen_ledger_residual_kg=coarse['oxygen_balance_error_kg'],maximum_carbon_ledger_residual_kg=coarse['carbon_balance_error_kg'],
                        water_boundary_continuity_residual_m3_day=water_error,water_scope='Fixed storage and boundary flows are assumed; this is a dimensional/continuity check, not observed hydrology.',
                        nonnegative_minimum_oxygen=bool(np.min(coarse['minimum'])>=0),
                        minimum_river_half_step_diagnostic='PASS' if difference<=.005 else 'EXCEEDS 0.005 mg/L: retained solver first-32 diagnostic does not guarantee all members'))
result=dict(kind='Software/numerical model audit, not environmental validation',scenarios=records,stoichiometry_kg_O2_per_kg_C=RATIO,
            published_parameter_source=read_json('provenance/flood_parameters.json'),
            limitations=['Convergence checks minimum river oxygen only, not every quantity/trajectory or every sensitivity hybrid',
                         'All-released-carbon biodegradable assumption and omitted processes are not validated by mass balance',
                         'Input independence, ranges, fixed hydrology and mixing remain assumptions; sensitivity ranks are conditional',
                         'DODOC/BRAT-informed simplified implementation; not a reproduction of their calibrated routing models'])
(SNAPSHOT_ROOT/'derived/model_audit_03.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print([(r['scenario'],r['max_minimum_river_difference_mg_l'],r['minimum_river_half_step_diagnostic']) for r in records])
