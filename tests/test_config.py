"""
test_config.py
--------------
Unit tests for glacier_snow_analysis.config.
"""

import pytest
from pathlib import Path

from glacier_snow_analysis.config import (
    PipelineConfig,
    MaskConfig,
    TimeseriesConfig,
    JobConfig,
    load_config,
)


class TestDefaults:
    def test_default_ndsi_threshold(self):
        cfg = PipelineConfig()
        assert cfg.timeseries.ndsi_threshold == 0.4

    def test_default_cloud_cover(self):
        cfg = PipelineConfig()
        assert cfg.mask.cloud_cover_max == 20

    def test_default_retries(self):
        cfg = PipelineConfig()
        assert cfg.job.max_retries == 3

    def test_derived_paths(self):
        cfg = PipelineConfig(glacier_name="TestGlacier", data_path="/tmp/out")
        assert cfg.nc_path == Path("/tmp/out/TestGlacier_glacier_masked.nc")
        assert cfg.csv_path == Path("/tmp/out/min_SCF_TestGlacier.csv")


class TestLoadConfig:
    def test_missing_file_returns_defaults(self):
        cfg = load_config("/nonexistent/path/config.yaml")
        assert isinstance(cfg, PipelineConfig)

    def test_none_returns_defaults(self):
        cfg = load_config(None)
        assert isinstance(cfg, PipelineConfig)

    def test_yaml_overrides(self, tmp_path):
        yaml_content = """
glacier_name: Viedma
data_path: /tmp/viedma
timeseries:
  ndsi_threshold: 0.5
  temporal_start: "2020-01-01"
  temporal_end:   "2023-12-31"
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml_content)

        cfg = load_config(cfg_file)
        assert cfg.glacier_name == "Viedma"
        assert cfg.data_path == "/tmp/viedma"
        assert cfg.timeseries.ndsi_threshold == 0.5
        assert cfg.timeseries.temporal_start == "2020-01-01"

    def test_partial_yaml_keeps_defaults(self, tmp_path):
        yaml_content = "glacier_name: PartialTest\n"
        cfg_file = tmp_path / "partial.yaml"
        cfg_file.write_text(yaml_content)

        cfg = load_config(cfg_file)
        assert cfg.glacier_name == "PartialTest"
        assert cfg.timeseries.ndsi_threshold == 0.4   # default preserved
