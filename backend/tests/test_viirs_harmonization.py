import numpy as np
import pandas as pd
import pytest

from pyro.harmonize import calibrate, harmonize


def overlap():
    # Union/MODIS=3, union/VIIRS=1.2. Using the MODIS factor for VIIRS triples it.
    return pd.DataFrame([
        {'period_year': y, 'period_index': m, 'modis_cd': 10., 'viirs_cd': 25., 'union_cd': 30.}
        for y in range(2012, 2018) for m in (1, 2)
    ])


def test_separate_calibration_for_each_sensor():
    train = overlap()
    cal = calibrate(train, 'cell_days', 2012, 2017, 5, 5)
    assert cal.factor(1)[0] == pytest.approx(3)
    assert cal.factor_viirs(1)[0] == pytest.approx(1.2)
    extra = pd.DataFrame([{'period_year': 2026, 'period_index': 1, 'modis_cd': 0., 'viirs_cd': 50., 'union_cd': 50.}])
    result = harmonize(extra, cal).iloc[0]
    assert result['value'] == pytest.approx(60)
    assert result['factor'] == pytest.approx(1.2)
    assert result['estimated'] and not result['factor_fallback']


def test_viirs_fallback_and_missing_calibration():
    train = overlap().iloc[:3]
    cal = calibrate(train, 'cell_days', 2012, 2017, 5, 5)
    row = pd.DataFrame([{'period_year': 2026, 'period_index': 10, 'modis_cd': 0., 'viirs_cd': 20., 'union_cd': 20.}])
    result = harmonize(row, cal).iloc[0]
    assert result['value'] == pytest.approx(24) and result['factor_fallback']
    insufficient = calibrate(train.iloc[:2], 'cell_days', 2012, 2017, 5, 5)
    missing = harmonize(row, insufficient).iloc[0]
    assert np.isnan(missing['value']) and np.isnan(missing['factor'])
    # An explicit single-sensor view displays observed data, not an invented estimate.
    raw = harmonize(row, insufficient, sources='viirs').iloc[0]
    assert raw['value'] == 20 and not raw['estimated']


@pytest.mark.parametrize('measure,prefix', [('cell_days', 'cd'), ('detections', 'det')])
@pytest.mark.parametrize('period', [1, 43])  # either month or ISO week index
def test_sensor_factors_for_both_measures_and_period_types(measure, prefix, period):
    train = pd.DataFrame([{'period_year': y, 'period_index': period,
                           f'modis_{prefix}': 10., f'viirs_{prefix}': 25., f'union_{prefix}': 30.}
                          for y in range(2012, 2018)])
    cal = calibrate(train, measure, 2012, 2017, 5, 5)
    row = pd.DataFrame([{'period_year': 2026, 'period_index': period,
                         f'modis_{prefix}': 0., f'viirs_{prefix}': 50., f'union_{prefix}': 50.}])
    out = harmonize(row, cal).iloc[0]
    assert out.value == pytest.approx(60) and out.estimated
    assert out.value_low == pytest.approx(60) and out.value_high == pytest.approx(60)

