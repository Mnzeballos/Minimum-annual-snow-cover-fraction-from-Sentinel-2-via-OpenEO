"""
conftest.py
-----------
Shared pytest fixtures for the glacier-snow-analysis test suite.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture()
def sample_timeseries_json(tmp_path) -> Path:
    """Write a minimal timeseries.json and return its path."""
    data = {
        "2019-08-01": [[1000, 50, 300]],
        "2019-12-15": [[1000, 10, 800]],
        "2020-07-20": [[1000, 80, 150]],
        "2020-11-03": [[1000, 5,  600]],
        "2021-09-10": [[1000, 20, 400]],
        "2021-12-01": [[1000, 15, 900]],
    }
    p = tmp_path / "timeseries.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture()
def sample_geojson(tmp_path) -> Path:
    """Write a minimal glacier GeoJSON and return its path."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-73.1, -50.5],
                        [-73.0, -50.5],
                        [-73.0, -50.4],
                        [-73.1, -50.4],
                        [-73.1, -50.5],
                    ]],
                },
                "properties": {"DN": 1},
            }
        ],
    }
    p = tmp_path / "glacier.geojson"
    p.write_text(json.dumps(geojson))
    return p
