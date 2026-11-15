"""Límites simplificados y consistencia del filtro departamental."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
from fastapi.testclient import TestClient

from pyro import departments, nrt
from pyro.store import Dataset


def test_departments_are_real_polygons_and_include_lima_ayacucho():
    all_zones = departments.all_departments()
    assert len(all_zones) == 25
    assert all_zones['d_15']['name'] == 'Lima'
    assert all_zones['d_05']['name'] == 'Ayacucho'
    assert '2007' in all_zones['d_15']['note']
    points = pd.DataFrame({'lat': [-12.0464, -13.1631, -12.05],
                           'lon': [-77.0428, -74.2236, -77.13], 'name': ['Lima', 'Ayacucho', 'Callao']})
    assert departments.filter_frame(points, 'd_15')['name'].tolist() == ['Lima']
    assert departments.filter_frame(points, 'd_05')['name'].tolist() == ['Ayacucho']
    assert departments.filter_frame(points, 'd_07')['name'].tolist() == ['Callao']


def test_ring_handles_boundary_and_hole(monkeypatch):
    geometry = {'type': 'Polygon', 'coordinates': [[[0,0],[4,0],[4,4],[0,4],[0,0]],
                                                    [[1,1],[3,1],[3,3],[1,3],[1,1]]]}
    monkeypatch.setattr(departments, 'all_departments', lambda: {'d_test': {'bbox': [0,0,4,4], 'geometry': geometry}})
    df = pd.DataFrame({'lon': [0, 0.5, 2, 1, 5], 'lat': [0, 0.5, 2, 2, 2]})
    assert departments.filter_frame(df, 'd_test').index.tolist() == [0, 1, 3]


def test_api_filters_historic_recent_and_csv(monkeypatch, tmp_path):
    import copy
    import api.main as main
    from pyro.config import Config
    cfg = copy.deepcopy(main.cfg.raw)
    cfg['api']['data_file'] = str(tmp_path / 'detections.parquet')
    monkeypatch.setattr(main, 'cfg', Config(cfg))
    cols = ['day','lat','lon','source','conf_level','conf_raw','frp','ftype']
    df = pd.DataFrame([[20000,-12.0464,-77.0428,2,2,-1,50.,0],
                       [20000,-13.1631,-74.2236,2,2,-1,80.,0],
                       [20000,-12.05,-77.13,2,2,-1,20.,0]], columns=cols)
    parent = Dataset(df, '', '')
    monkeypatch.setattr(main, 'dataset', lambda: parent)
    main._department_dataset.cache_clear()
    bbox = main.cfg.zone_bbox('peru')
    nrt.save_recent(main.cfg, df, nrt.NRT_SOURCES, 3, bbox=bbox)
    client = TestClient(main.app)
    assert len([z for z in client.get('/api/meta').json()['zones'] if z.get('kind') == 'department']) == 25
    assert client.get('/api/departments/d_05').json()['properties']['name'] == 'Ayacucho'
    for key in ('d_15','d_05','d_07'):
        data = client.get('/api/hotspots', params={'zone': key}).json()
        assert data['meta']['total'] == 1
        recent = client.get('/api/recent', params={'zone': key}).json()
        assert recent['total'] == 1
        recent_map = client.get('/api/recent/hotspots', params={'zone': key}).json()
        assert recent_map['meta']['total'] == 1
        csv = client.get('/api/csv/hotspots', params={'zone': key})
        assert csv.status_code == 200 and csv.headers['x-total-rows'] == '1'
        calendar = client.get('/api/calendar', params={'zone': key})
        assert calendar.status_code == 200 and calendar.json()['cards']['total_detections'] == 1
        assert calendar.json()['cards']['last_month']['level'] is None
        question = client.post('/api/assistant', json={'question': 'hay focos recientes?', 'zone': key})
        assert question.status_code == 200 and '1 detecciones' in question.json()['answer']
    main._department_dataset.cache_clear()


def test_cells_only_computed_once_concurrently(monkeypatch):
    import time
    from pyro import grid
    calls = []
    monkeypatch.setattr(grid, 'build_cells', lambda frame, size: (calls.append(1), time.sleep(0.05), pd.DataFrame())[2])
    dataset = Dataset(pd.DataFrame(), '', '')
    with ThreadPoolExecutor(max_workers=8) as pool:
        cells = list(pool.map(lambda _: dataset.cells, range(8)))
    assert len(calls) == 1
    assert all(c is cells[0] for c in cells)


def test_recent_last_week_uses_actual_utc_not_latest_old_day(tmp_path):
    import copy
    from pyro.config import Config, load_config
    raw = copy.deepcopy(load_config().raw)
    raw['api']['data_file'] = str(tmp_path / 'detections.parquet')
    cfg = Config(raw)
    cols = ['day','lat','lon','source','conf_level','conf_raw','frp','ftype']
    old = pd.DataFrame([[10000,-12.0464,-77.0428,2,2,-1,40.,0]], columns=cols)
    nrt.save_recent(cfg, old, nrt.NRT_SOURCES, 3, bbox=cfg.zone_bbox('peru'))
    stats = nrt.stats(cfg, cfg.zone_bbox('peru'))
    assert stats['total'] == 1
    assert stats['last_7_days'] == 0
