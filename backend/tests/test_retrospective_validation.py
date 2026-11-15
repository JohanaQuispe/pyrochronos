"""El año evaluado nunca debe influir en su propio factor."""
import copy
import importlib.util
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from pyro.config import Config, load_config

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'validacion_retrospectiva.py'
spec = importlib.util.spec_from_file_location('validacion_retrospectiva', SCRIPT)
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def config():
    raw = copy.deepcopy(load_config().raw)
    raw['sources']['overlap_start'] = '2012-01-01'
    raw['sources']['overlap_end'] = '2018-12-31'
    raw['harmonization']['shrink_min_years'] = 5
    raw['harmonization']['min_periods_for_factor'] = 5
    return Config(raw)


def aggregated():
    rows = []
    for year in range(2012, 2019):
        for month in range(1, 13):
            union = 100 if year == 2018 else 20
            rows.append({'period_year': year, 'period_index': month,
                         'modis_cd': 10, 'viirs_cd': union - 10, 'union_cd': union})
    return pd.DataFrame(rows)


def test_holdout_year_never_used_in_factors():
    results = validation.validate(aggregated(), config(), date(2000,1,1), date(2018,12,31))
    target = next(r for r in results['years'] if r['year'] == 2018)
    assert target['observed'] == 1200
    assert target['estimated'] == 240
    assert target['absolute_error_pct'] == pytest.approx(80)
    assert target['signed_error_pct'] == pytest.approx(-80)
    assert target['fallback_months'] == 0
    assert results['median_ape'] == pytest.approx(0)
    assert len(results['years']) == 7


def test_partial_and_missing_sensor_excluded():
    agg = aggregated()
    agg.loc[(agg.period_year == 2016) & (agg.period_index == 9), 'viirs_cd'] = 0
    agg = agg[~((agg.period_year == 2015) & (agg.period_index == 3))]
    result = validation.validate(agg, config(), date(2000,1,1), date(2018,8,1))
    excluded = dict(result['skipped'])
    assert 2015 in excluded and 2016 in excluded and 2018 in excluded
    assert all(r['year'] not in (2015, 2016, 2018) for r in result['years'])


def test_not_enough_training_data_is_not_faked():
    agg = aggregated()
    agg.loc[agg.period_year != 2018, 'viirs_cd'] = 0
    result = validation.validate(agg, config(), date(2000,1,1), date(2018,12,31))
    assert result['years'] == []
    assert result['median_ape'] is None
    assert 'menos de 3' in dict(result['skipped'])[2018]
