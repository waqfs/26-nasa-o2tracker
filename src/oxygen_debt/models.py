"""Educational oxygen mass balance with explicit assumptions and oxygen limitation."""
from dataclasses import dataclass, asdict
import math
import numpy as np
from scipy.integrate import solve_ivp

def freshwater_equilibrium(temperature_c):
    """APHA/QUAL2E temperature relationship documented by USACE HEC-RAS §6.1.

    Freshwater, standard atmospheric pressure. This is a reference concentration,
    not a field sensor's pressure/salinity-corrected saturation estimate.
    """
    temperature = np.asarray(temperature_c, dtype=float)
    if np.any(~np.isfinite(temperature)) or np.any((temperature < 0) | (temperature > 40)):
        raise ValueError('Temperature must be finite and between 0 and 40 Celsius')
    kelvin = temperature + 273.15
    return np.exp(-139.34411 + 1.575701e5/kelvin - 6.642308e7/kelvin**2
                  + 1.243800e10/kelvin**3 - 8.621949e11/kelvin**4)

@dataclass(frozen=True)
class Scenario:
    temperature_c: float = 20
    initial_oxygen_mg_l: float = 9
    initial_demand_mg_l: float = 8
    incoming_oxygen_mg_l: float = 9
    incoming_demand_mg_l: float = 2
    exchange_per_day: float = .2
    decay_20_per_day: float = .15
    reaeration_20_per_day: float = .5
    oxygen_half_saturation_mg_l: float = .2
    days: float = 14

def simulate(scenario: Scenario):
    parameters = asdict(scenario)
    if any(not math.isfinite(v) for v in parameters.values()):
        raise ValueError('Scenario parameters must be finite')
    if not 0 <= scenario.temperature_c <= 40 or not 0 < scenario.days <= 60:
        raise ValueError('Scenario temperature/time outside supported range')
    if any(value < 0 for key,value in parameters.items() if key not in ['temperature_c','days']):
        raise ValueError('Concentrations and rate parameters must be nonnegative')
    if scenario.oxygen_half_saturation_mg_l <= 0:
        raise ValueError('Oxygen half-saturation must be positive')
    equilibrium = float(freshwater_equilibrium(scenario.temperature_c))
    decay = scenario.decay_20_per_day * 1.047**(scenario.temperature_c-20)
    aeration = scenario.reaeration_20_per_day * 1.024**(scenario.temperature_c-20)
    def balance(_, state):
        oxygen, demand, consumed, air, exchanged = state
        available = max(oxygen,0)
        reaction = decay * max(demand,0) * available/(scenario.oxygen_half_saturation_mg_l+available)
        uptake = aeration*(equilibrium-oxygen)
        exchange = scenario.exchange_per_day*(scenario.incoming_oxygen_mg_l-oxygen)
        return [uptake+exchange-reaction,
                scenario.exchange_per_day*(scenario.incoming_demand_mg_l-demand)-reaction,
                reaction,uptake,exchange]
    times = np.linspace(0,scenario.days,281)
    solution = solve_ivp(balance,[0,scenario.days],[scenario.initial_oxygen_mg_l,scenario.initial_demand_mg_l,0,0,0],
                         t_eval=times,rtol=1e-8,atol=1e-10,max_step=.1)
    if not solution.success or solution.y[0].min() < -1e-7:
        raise RuntimeError('Scenario integration failed')
    oxygen,demand,consumed,air,exchange = solution.y
    residual = oxygen-(scenario.initial_oxygen_mg_l+air+exchange-consumed)
    return dict(kind='MODELED EDUCATIONAL SCENARIO',calibration='No site calibration',parameters=parameters,
                equilibrium_mg_l=equilibrium,decay_per_day=decay,reaeration_per_day=aeration,
                units=dict(time='days',oxygen='mg/L',demand='mg O2-equivalent/L',rates='1/day'),
                time_days=times.tolist(),oxygen_mg_l=oxygen.tolist(),demand_mg_l=demand.tolist(),
                cumulative_consumed_mg_l=consumed.tolist(),mass_balance_max_error_mg_l=float(abs(residual).max()),
                minimum_oxygen_mg_l=float(oxygen.min()),
                assumptions=['Completely mixed fixed-volume box','Freshwater at standard pressure',
                             'Demand is oxygen-equivalent biodegradable loading, not measured DOC',
                             'Oxygen-limited first-order demand consumption','No algae, stratification, sediment demand or explicit flow network',
                             'Temperature multipliers and all rates are illustrative user assumptions',
                             'DODOC/BRAT concepts inform the process selection; this is a separate simplified implementation'])
