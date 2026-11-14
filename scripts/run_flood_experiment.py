"""Regenerate frozen educational scenarios without target-oxygen fitting."""
import json
from dataclasses import replace
from oxygen_debt.flood import FloodExperiment, experiment
from oxygen_debt.settings import SNAPSHOT_ROOT

configuration=FloodExperiment()
results={'default':experiment(configuration),
         'disconnected':experiment(replace(configuration,connected_fraction=0,hydrology_spread=0)),
         'low_flow_large_area':experiment(replace(configuration,area_ha=1000,river_flow_m3_s=5,river_volume_ml=500,connected_fraction=1,hydrology_spread=.25))}
(SNAPSHOT_ROOT/'derived/flood_experiment.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
for name,result in results.items():
    print(name,{k:result[k] for k in ['potential_oxygen_demand_kg','minimum_river_oxygen_mg_l','minimum_floodplain_oxygen_mg_l','most_informative_parameter','refinement_32_members_max_minimum_difference_mg_l']})
