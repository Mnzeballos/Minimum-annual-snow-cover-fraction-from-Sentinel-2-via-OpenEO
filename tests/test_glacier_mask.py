"""
test_glacier_mask.py
--------------------
Unit tests for glacier_snow_analysis.glacier_mask.
Only tests the parts that don't require an OpenEO connection.
"""

import json
import pytest
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from pathlib import Path

from glacier_snow_analysis.glacier_mask import load_glacier_outline, raster_to_geojson


class TestLoadGlacierOutline:
    def test_loads_valid_geojson(self, sample_geojson):
        import geopandas as gpd
        gdf = load_glacier_outline(sample_geojson)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 1

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            load_glacier_outline(tmp_path / "missing.geojson")


class TestRasterToGeojson:
    def _write_raster(self, path: Path, data: np.ndarray) -> Path:
        """Helper: write a tiny single-band GeoTIFF."""
        transform = from_bounds(-73.1, -50.5, -73.0, -50.4, data.shape[1], data.shape[0])
        with rasterio.open(
            path, "w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data, 1)
        return path

    def test_creates_geojson(self, tmp_path):
        data = np.ones((10, 10), dtype=np.float32)
        raster = self._write_raster(tmp_path / "mask.tif", data)
        out = tmp_path / "mask.geojson"
        result = raster_to_geojson(raster, out)
        assert result.exists()
        loaded = json.loads(result.read_text())
        assert loaded["type"] == "FeatureCollection"

    def test_raises_on_empty_raster(self, tmp_path):
        data = np.zeros((10, 10), dtype=np.float32)
        raster = self._write_raster(tmp_path / "empty.tif", data)
        with pytest.raises(ValueError, match="No valid glacier polygons"):
            raster_to_geojson(raster, tmp_path / "out.geojson")
