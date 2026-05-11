"""
config.py
---------
Typed configuration for the glacier-snow pipeline.

Configs are loaded from a YAML file and validated via a dataclass.
Sensible defaults are provided so the file only needs to override
what differs from the defaults.

Example YAML
------------
glacier_name: Perito_Moreno
glacier_path: ./data/perito_moreno_glacier.geojson
data_path: ./results

mask:
  temporal_start: "2018-02-15"
  temporal_end:   "2018-03-15"
  cloud_cover_max: 20

timeseries:
  temporal_start: "2018-02-01"
  temporal_end:   "2024-06-30"
  cloud_cover_max: 20
  ndsi_threshold:  0.4

job:
  max_retries: 3
  retry_delay_seconds: 60

logging:
  level: INFO
  log_file: null          # set to a path string to enable file logging
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-configs
# ---------------------------------------------------------------------------

@dataclass
class MaskConfig:
    temporal_start: str = "2018-02-15"
    temporal_end:   str = "2018-03-15"
    cloud_cover_max: int = 20


@dataclass
class TimeseriesConfig:
    temporal_start: str = "2018-02-01"
    temporal_end:   str = "2024-06-30"
    cloud_cover_max: int = 20
    ndsi_threshold:  float = 0.4


@dataclass
class JobConfig:
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    glacier_name: str = "Glacier"
    glacier_path: str = "./data/glacier.geojson"
    data_path:    str = "./results"
    skip_mask:    bool = False

    mask:       MaskConfig       = field(default_factory=MaskConfig)
    timeseries: TimeseriesConfig = field(default_factory=TimeseriesConfig)
    job:        JobConfig        = field(default_factory=JobConfig)
    logging:    LoggingConfig    = field(default_factory=LoggingConfig)

    # Derived convenience properties
    @property
    def data_dir(self) -> Path:
        return Path(self.data_path)

    @property
    def nc_path(self) -> Path:
        return self.data_dir / f"{self.glacier_name}_glacier_masked.nc"

    @property
    def geojson_mask_path(self) -> Path:
        return self.data_dir / f"{self.glacier_name}_glacier_masked.geojson"

    @property
    def results_dir(self) -> Path:
        return self.data_dir / f"results_{self.glacier_name}"

    @property
    def csv_path(self) -> Path:
        return self.data_dir / f"min_SCF_{self.glacier_name}.csv"

    @property
    def plot_path(self) -> Path:
        return self.data_dir / f"min_SCF_{self.glacier_name}.png"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | Path | None = None) -> PipelineConfig:
    """
    Load a ``PipelineConfig`` from a YAML file.

    If *path* is ``None``, or the file does not exist, the default
    configuration is returned and a warning is logged.

    Parameters
    ----------
    path : str | Path | None
        Path to a YAML configuration file.

    Returns
    -------
    PipelineConfig
    """
    if path is None:
        logger.warning("No config file provided — using default configuration.")
        return PipelineConfig()

    path = Path(path)
    if not path.exists():
        logger.warning("Config file not found at %s — using defaults.", path)
        return PipelineConfig()

    if not _YAML_AVAILABLE:
        raise ImportError(
            "PyYAML is required to load config files: pip install pyyaml"
        )

    with open(path) as f:
        raw: dict = yaml.safe_load(f) or {}

    logger.info("Loaded config from %s", path)

    def _sub(cls, key):
        return cls(**raw.get(key, {})) if raw.get(key) else cls()

    return PipelineConfig(
        glacier_name = raw.get("glacier_name", PipelineConfig.glacier_name),
        glacier_path = raw.get("glacier_path", PipelineConfig.glacier_path),
        data_path    = raw.get("data_path",    PipelineConfig.data_path),
        skip_mask    = raw.get("skip_mask",    PipelineConfig.skip_mask),
        mask         = _sub(MaskConfig,       "mask"),
        timeseries   = _sub(TimeseriesConfig, "timeseries"),
        job          = _sub(JobConfig,        "job"),
        logging      = _sub(LoggingConfig,    "logging"),
    )
