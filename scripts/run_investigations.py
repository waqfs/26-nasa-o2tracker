"""Reproduce the oxygen investigation from the supplied observation snapshot."""
import json
from pathlib import Path
from oxygen_debt.investigation import load_data, compare, daily_covariates
from oxygen_debt.models import simulate, Scenario
from oxygen_debt.settings import SNAPSHOT_ROOT

def main():
    stations,locations = load_data()
    results = dict(hypothesis='NISAR adds explanatory/predictive oxygen information',verdict='INSUFFICIENT DATA',
                   independent_radar_dates=3,p_value=None,radar_oxygen_correlations=None,
                   reason='Only three independent radar epochs; spatial blocks and daily repetition cannot supply more independent temporal pairs.',
                   daily_covariates={s['id']:daily_covariates(s) for s in stations['stations']},
                   alignments=[compare(s['id'],'candidate-2',lag_days=lag) for s in stations['stations'] for lag in [0,3,7]],
                   lag_policy='0, 3 and 7 days are descriptive sensitivity windows, without inference or lag selection for significance.',
                   educational_scenario=simulate(Scenario()))
    path=SNAPSHOT_ROOT/'derived/oxygen_results.json'
    path.write_text(json.dumps(results,indent=2,allow_nan=False),encoding='utf-8')
    for station,summary in results['daily_covariates'].items():
        print(station,'daily pairs',summary['n'],'Pearson',round(summary['pearson'],3),'Spearman',round(summary['spearman'],3),
              'differenced',round(summary['first_difference_pearson'],3),summary['evaluation']['metrics'])
    print(results['verdict'])

if __name__=='__main__':main()
