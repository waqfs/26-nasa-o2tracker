"""Align actual radar/ground observations with explicit temporal and spatial scope."""
from datetime import datetime, timedelta, timezone
import numpy as np
from pyproj import Transformer
from scipy.stats import spearmanr
from .settings import read_json
from .models import freshwater_equilibrium

def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Observation timestamps require an explicit timezone')
    return parsed.astimezone(timezone.utc)

def good_rows(variable):
    return [row for row in variable.get('observations',[]) if row['grade']=='GOOD'
            and row['value'] is not None and np.isfinite(row['value'])]

def load_data():
    return read_json('derived/stations.json'), read_json('derived/investigation.json')

def select_station(data, identifier):
    return next(station for station in data['stations'] if station['id']==identifier)

def correlation_summary(x, y, independent_epochs, minimum=10):
    """Conservative display guard. A threshold is not a power calculation."""
    if independent_epochs < minimum:
        return dict(status='INSUFFICIENT DATA',paired_values=len(x),independent_radar_epochs=independent_epochs,
                    pearson=None,spearman=None,p_value=None,
                    reason=f'Only {independent_epochs} independent radar dates. Daily repeats and geographic blocks cannot increase the temporal sample size. Display guard requires at least {minimum}; power and dependence would still need assessment.')
    if len(x)<minimum or np.std(x)==0 or np.std(y)==0:
        return dict(status='INSUFFICIENT DATA',pearson=None,spearman=None,p_value=None)
    return dict(status='EXPLORATORY',pearson=float(np.corrcoef(x,y)[0,1]),spearman=float(spearmanr(x,y).statistic),p_value=None)

def compare(station_id, location_id, variable='oxygen', polarization='HHHH', lag_days=0, window_days=1, mode='retrospective'):
    station_data, radar_data = load_data()
    station = select_station(station_data,station_id)
    location = next(item for item in radar_data['locations'] if item['id']==location_id)
    if polarization not in ['HHHH','HVHV'] or variable not in ['oxygen','temperature','level']:
        raise ValueError('Unsupported observation variable')
    if not -14 <= lag_days <= 21 or not 1 <= window_days <= 7 or mode not in ['retrospective','as_of']:
        raise ValueError('Unsupported lag, window or mode')
    series = station['variables'].get(variable)
    rows = good_rows(series) if series else []
    coordinate_transform = Transformer.from_crs(4283,32754,always_xy=True)
    station_xy = coordinate_transform.transform(station['longitude'],station['latitude'])
    target_xy = Transformer.from_crs(4326,32754,always_xy=True).transform(location['lon'],location['lat'])
    distance = float(np.linalg.norm(np.array(station_xy)-np.array(target_xy)))
    pairs = []
    for observation in location['nisar']:
        acquired = timestamp(observation['time'])
        target = acquired + timedelta(days=lag_days)
        # A window begins at the requested lag. For one day, allow nearest timestamp within 12h.
        candidates = [row for row in rows if target-timedelta(hours=12) <= timestamp(row['time'])
                      < target+timedelta(days=window_days)-timedelta(hours=12)]
        allowed = [row for row in candidates if mode=='retrospective' or timestamp(row['time'])<=acquired]
        value = float(np.mean([row['value'] for row in allowed])) if allowed else None
        pairs.append(dict(radar_time=observation['time'],radar_db=observation[polarization],granule_id=observation['granule_id'],
                          target_utc=target.isoformat(),ground_mean=value,ground_times=[row['time'] for row in allowed],
                          ground_values=[row['value'] for row in allowed],time_differences_hours=[(timestamp(row['time'])-acquired).total_seconds()/3600 for row in allowed],
                          count=len(allowed),blocked_future_count=len(candidates)-len(allowed),
                          status='AVAILABLE' if allowed else 'FUTURE DATA BLOCKED' if candidates else 'MISSING OR NOT GOOD',
                          aggregation='Arithmetic mean of retained GOOD daily aggregates'))
    valid = [p for p in pairs if p['ground_mean'] is not None]
    stats = correlation_summary([p['radar_db'] for p in valid],[p['ground_mean'] for p in valid],len(valid))
    return dict(station=station_id,station_name=station['name'],location=location_id,location_name=location['name'],
                variable=variable,unit=series['unit'] if series else None,polarization=polarization,
                lag_days=lag_days,window_days=window_days,mode=mode,pairs=pairs,statistics=stats,distance_m=distance,
                connectivity='UNVERIFIED. Geographic distance is not hydraulic connectivity.',
                temporal_caution='Daily aggregate window convention and historical product delivery times remain unverified. As-of mode checks recorded timestamps only.',
                evidence={'radar_oxygen_relationship':'INSUFFICIENT DATA','radar_proves_inundation':'INCONCLUSIVE',
                          'oxygen_depletion_event':'INCONCLUSIVE for short-duration minima',
                          'daily_means_below_2_mg_l':'CONTRADICTED by the retained GOOD daily means'},
                missing=['Additional independent radar dates','Wetland outlet DO/DOC and flow','Hydraulic travel-time/connectivity evidence','Matched inundation labels'],
                source=series['source'] if series else None)

def daily_covariates(station):
    oxygen = {row['time']:row['value'] for row in good_rows(station['variables']['oxygen'])}
    temperature = {row['time']:row['value'] for row in good_rows(station['variables'].get('temperature',{}))}
    times = sorted(oxygen.keys() & temperature.keys(),key=timestamp)
    y = np.array([oxygen[t] for t in times]);x = np.array([temperature[t] for t in times])
    if len(times)<20:
        return dict(status='INSUFFICIENT DATA',n=len(times))
    pearson = float(np.corrcoef(x,y)[0,1]);spearman = float(spearmanr(x,y).statistic)
    delta_r = float(np.corrcoef(np.diff(x),np.diff(y))[0,1])
    split = len(y)*2//3
    train = np.c_[np.ones(split),x[:split]]
    beta = np.linalg.lstsq(train,y[:split],rcond=None)[0]
    predictions = {'temperature_association':np.c_[np.ones(len(y)-split),x[split:]]@beta,
                   'training_mean':np.full(len(y)-split,y[:split].mean()),'previous_day_persistence':y[split-1:-1]}
    errors = {name:dict(mae_mg_l=float(np.abs(value-y[split:]).mean()),rmse_mg_l=float(np.sqrt(np.mean((value-y[split:])**2)))) for name,value in predictions.items()}
    equilibrium = freshwater_equilibrium(x)
    return dict(status='CONSISTENT BUT UNPROVEN',n=len(times),dates=[times[0],times[-1]],
                pearson=pearson,spearman=spearman,first_difference_pearson=delta_r,p_value=None,
                lag1_oxygen_autocorrelation=float(np.corrcoef(y[:-1],y[1:])[0,1]),
                evaluation=dict(training_days=split,test_days=len(y)-split,test_start=times[split],metrics=errors,
                    interpretation='Chronological descriptive benchmark. Temperature uses the same day sensor reading, so it is an explanatory covariate. Persistence uses prior-day DO. No radar covariate is fitted.'),
                oxygen_range=[float(y.min()),float(y.max())],temperature_range=[float(x.min()),float(x.max())],
                reference_equilibrium_range=[float(equilibrium.min()),float(equilibrium.max())],
                caution='Serial dependence, shared seasonal trend and omitted flow/algae drivers prevent causal attribution or significance claims.')
