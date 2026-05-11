# Glacier Snow Cover Analysis

A Python package for computing the **minimum annual snow-cover fraction** on glaciers from Sentinel-2 imagery, using the [OpenEO](https://openeo.cloud/) API and Copernicus Dataspace.

Developed as part of the course *Retrieval of Biophysical Parameters from Optical and Radar Data* at the University of Pavia.

**Authors:** Geogr. Julieta del Mar Motter & Biol. Manuel Zeballos  
**Supervisor:** PhD Mattia Callegari

---

## How it works

The pipeline runs four steps automatically:

1. **Glacier mask** — downloads a Sentinel-2 scene and applies spectral thresholds (Red/SWIR > 2.7 and Blue > 0.095) to isolate ice from the surrounding terrain, then converts the result to a GeoJSON polygon.
2. **Snow time series** — computes the NDSI (Normalized Difference Snow Index) for every available cloud-free scene over the full temporal range and aggregates pixel counts (total, cloud, snow) to the catchment level via an OpenEO batch job.
3. **Post-processing** — loads the batch job results, computes daily snow-cover fractions, and extracts the yearly minimum.
4. **Visualisation** — saves a plot and a CSV of the annual minimum snow-cover fraction.

> You can skip step 1 and provide your own glacier outline directly (e.g. from the [Randolph Glacier Inventory](https://www.glims.org/RGI/)).

---

## Requirements

- Python ≥ 3.10
- A free [Copernicus Dataspace](https://dataspace.copernicus.eu) account (for OpenEO access)
- A glacier outline in GeoJSON format (EPSG:4326)

---

## Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/your-username/glacier-snow-analysis.git
cd glacier-snow-analysis
pip install -e ".[dev]"
```

Verify the installation:

```bash
python -c "import glacier_snow_analysis; print('OK')"
```

---

## Quick start

### 1. Configure

Copy the example config and edit it:

```bash
cp config.example.yaml config.yaml
```

Open `config.yaml` and set at minimum:

```yaml
glacier_name: Perito_Moreno
glacier_path: /absolute/path/to/your/glacier_outline.geojson
data_path:    ./results

timeseries:
  temporal_start: "2018-02-01"
  temporal_end:   "2024-06-30"
```

> **Use absolute paths** for `glacier_path` to avoid ambiguity regardless of where you run the command.

### 2. Run

```bash
glacier-snow --config config.yaml
```

On first run, a browser window will open asking you to log in with your Copernicus Dataspace account. Credentials are cached locally after that.

You will see live progress in the terminal:

```
2026-05-11 10:00:01 | INFO | glacier_snow_analysis.cli | Starting pipeline for 'Perito_Moreno'
2026-05-11 10:00:03 | INFO | glacier_snow_analysis.cli | === STEP 1: Glacier mask ===
2026-05-11 10:02:10 | INFO | glacier_snow_analysis.cli | === STEP 2: Snow time series ===
2026-05-11 10:18:44 | INFO | glacier_snow_analysis.cli | === STEP 3: Post-processing ===
2026-05-11 10:18:45 | INFO | glacier_snow_analysis.cli | === STEP 4: Visualisation ===
2026-05-11 10:18:46 | INFO | glacier_snow_analysis.cli | Pipeline complete. All outputs in: ./results
```

### 3. Outputs

All files are saved to `data_path`:

| File | Description |
|---|---|
| `{name}_glacier_masked.nc` | Raw glacier mask raster |
| `{name}_glacier_masked.geojson` | Glacier outline derived from the mask |
| `results_{name}/timeseries.json` | Raw pixel counts from the OpenEO batch job |
| `min_SCF_{name}.csv` | Yearly minimum snow-cover fractions |
| `min_SCF_{name}.png` | Plot of annual minimums |

---

## Configuration reference

All options with their defaults:

```yaml
glacier_name: Glacier          # used to name output files
glacier_path: ./data/glacier.geojson
data_path:    ./results
skip_mask:    false            # set true to use glacier_path as outline directly

mask:
  temporal_start:  "2018-02-15"   # date range used to build the glacier mask
  temporal_end:    "2018-03-15"   # (late summer = minimum snow, best for ice detection)
  cloud_cover_max: 20

timeseries:
  temporal_start:  "2018-02-01"   # full analysis period
  temporal_end:    "2024-06-30"
  cloud_cover_max: 20
  ndsi_threshold:  0.4            # pixels above this are classified as snow

job:
  max_retries:          3         # retry attempts for the OpenEO batch job
  retry_delay_seconds:  60        # wait time before first retry (doubles each attempt)

logging:
  level:    INFO                  # DEBUG, INFO, WARNING, ERROR
  log_file: null                  # set to a path to also write logs to a file
```

### Skip the mask step

If you already have a reliable glacier outline (e.g. from the RGI), you can skip step 1:

```yaml
skip_mask:    true
glacier_path: /path/to/rgi_outline.geojson
```

Or via the CLI flag:

```bash
glacier-snow --config config.yaml --skip-mask
```

---

## CLI flags

All config file options can also be passed as flags (config file takes precedence if both are provided):

```bash
glacier-snow \
  --glacier-name  Perito_Moreno \
  --glacier-path  /path/to/outline.geojson \
  --data-path     ./results \
  --mask-start    2018-02-15 \
  --mask-end      2018-03-15 \
  --ts-start      2018-02-01 \
  --ts-end        2024-06-30 \
  --log-level     DEBUG \
  --log-file      ./results/pipeline.log
```

---

## Use as a Python library

Each pipeline step is an importable function, so you can integrate them into your own scripts:

```python
from glacier_snow_analysis import (
    connect_openeo,
    load_timeseries,
    compute_snow_fractions,
    get_yearly_minimum,
    plot_minimum_snow_cover,
)

# Re-run only postprocessing on an existing result (no OpenEO call needed)
df = load_timeseries("./results/results_Perito_Moreno/timeseries.json")
df = compute_snow_fractions(df)
yearly_min = get_yearly_minimum(df, output_path="./results/min_SCF_Perito_Moreno.csv")
plot_minimum_snow_cover(yearly_min, "Perito Moreno")
```

---

## Project structure

```
glacier-snow-analysis/
├── glacier_snow_analysis/
│   ├── __init__.py         # Public API
│   ├── connection.py       # OpenEO authentication
│   ├── config.py           # Typed configuration (dataclass + YAML loader)
│   ├── logging_config.py   # Centralised logging setup
│   ├── retry.py            # Exponential back-off retry decorator
│   ├── glacier_mask.py     # Spectral glacier mask + raster → GeoJSON
│   ├── snow_analysis.py    # NDSI snow map + OpenEO batch job
│   ├── postprocessing.py   # Load results, compute fractions, yearly min
│   ├── visualization.py    # Matplotlib plots
│   └── cli.py              # Command-line entry point
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_postprocessing.py
│   ├── test_retry.py
│   └── test_glacier_mask.py
├── config.example.yaml
├── pyproject.toml
└── README.md
```

---

## Running the tests

```bash
pytest tests/ -v --cov=glacier_snow_analysis
```

The tests cover all local logic and do not require an OpenEO connection.

---

## Spectral thresholds

| Parameter | Value | Description |
|---|---|---|
| Red/SWIR ratio | > 2.7 | Ice/snow detection for glacier mask |
| Blue reflectance | > 0.095 | Excludes dark surfaces |
| NDSI threshold | > 0.4 | Snow classification in time series |
| Cloud SCL classes | 3, 8, 9 | Dark features, medium/high cloud probability |

These are sensible defaults for Patagonian glaciers. For other regions you may need to tune `ndsi_threshold` and the cloud cover settings in `config.yaml`.

---

## Citation

If you use this tool in your work, please cite:

> Motter, J.M. & Zeballos, M. (2026). *Glacier Snow Cover Analysis: a Python pipeline for minimum annual snow-cover fraction retrieval from Sentinel-2 via OpenEO*. University of Pavia. Supervised by Mattia Callegari.

---

## License

MIT
