"""
snow_analysis.py
----------------
Build the NDSI snow-cover process graph and submit batch jobs to OpenEO.
"""

from __future__ import annotations

import logging
from pathlib import Path

import openeo
from openeo.processes import lte

from .glacier_mask import load_glacier_outline
from .retry import retry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SNOW_COLLECTION = "SENTINEL2_L2A"
_SNOW_BANDS = ["B03", "B11", "SCL"]
_CLOUD_COVER_MAX = 20
_NDSI_THRESHOLD = 0.4
# SCL values for clouds / cloud shadows / dark features
_CLOUD_SCL_VALUES = (8, 9, 3)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def compute_snow_timeseries(
    conn: openeo.Connection,
    glacier_outline_path: str | Path,
    temporal_extent: list[str],
    cloud_cover_max: int = _CLOUD_COVER_MAX,
    ndsi_threshold: float = _NDSI_THRESHOLD,
) -> openeo.DataCube:
    """
    Build an OpenEO process graph that returns a time series of catchment-level
    pixel counts (total, cloud, snow) for the given glacier outline.

    The result is an aggregated JSON time series — **not yet downloaded**.
    Use :func:`run_batch_job` to submit and retrieve the results.

    Parameters
    ----------
    conn : openeo.Connection
        Authenticated OpenEO connection.
    glacier_outline_path : str | Path
        Path to the glacier outline GeoJSON (can be the auto-derived mask or
        the Randolph Glacier Inventory outline).
    temporal_extent : list[str]
        Two-element list [start_date, end_date].
    cloud_cover_max : int
        Maximum allowed cloud cover percentage.
    ndsi_threshold : float
        NDSI threshold above which a pixel is classified as snow.

    Returns
    -------
    openeo.DataCube
        Process graph ready for job submission.
    """
    logger.info(
        "Building snow time-series process graph for %s | %s → %s",
        glacier_outline_path, temporal_extent[0], temporal_extent[1],
    )
    catchment = load_glacier_outline(glacier_outline_path)
    bbox = catchment.bounds.iloc[0]

    spatial_extent = {
        "west": bbox[0], "east": bbox[2],
        "south": bbox[1], "north": bbox[3],
        "crs": 4326,
    }
    properties = {"eo:cloud_cover": lambda x: lte(x, cloud_cover_max)}

    s2 = conn.load_collection(
        _SNOW_COLLECTION,
        spatial_extent=spatial_extent,
        bands=_SNOW_BANDS,
        temporal_extent=temporal_extent,
        properties=properties,
    )

    green = s2.band("B03")
    swir = s2.band("B11")
    scl_band = s2.band("SCL")

    # NDSI and binary snow map
    ndsi = (green - swir) / (green + swir)
    snowmap = (ndsi > ndsi_threshold) * 1.0

    # Cloud mask (SCL classes 3, 8, 9)
    cloud_mask = (
        (scl_band == _CLOUD_SCL_VALUES[0])
        | (scl_band == _CLOUD_SCL_VALUES[1])
        | (scl_band == _CLOUD_SCL_VALUES[2])
    ) * 1.0

    snowmap_cloudfree = snowmap.mask(cloud_mask, replacement=2)
    snowmap_masked = snowmap_cloudfree.mask_polygon(catchment["geometry"][0])

    # Pixel count bands
    n_catchment = ((snowmap_cloudfree > -1) * 1.0).add_dimension(
        name="bands", type="bands", label="n_catchment"
    )
    n_cloud = cloud_mask.add_dimension(name="bands", type="bands", label="n_cloud")
    n_snow = ((snowmap_cloudfree == 1) * 1.0).add_dimension(
        name="bands", type="bands", label="n_snow"
    )

    combined = n_catchment.merge_cubes(n_cloud).merge_cubes(n_snow)
    n_pixels = combined.aggregate_spatial(
        geometries=catchment["geometry"][0], reducer="sum"
    )

    return n_pixels.save_result(format="JSON")


def run_batch_job(
    process_graph: openeo.DataCube,
    output_dir: str | Path,
    job_title: str = "snow_timeseries",
    max_retries: int = 3,
    retry_delay: float = 60.0,
) -> Path:
    """
    Submit an OpenEO process graph as a batch job, wait for completion,
    and download the results. Retries on transient failures.

    Parameters
    ----------
    process_graph : openeo.DataCube
        The process graph returned by :func:`compute_snow_timeseries`.
    output_dir : str | Path
        Directory where results will be downloaded.
    job_title : str
        Human-readable title for the batch job.
    max_retries : int
        Maximum number of submission attempts.
    retry_delay : float
        Seconds to wait before the first retry (doubles each attempt).

    Returns
    -------
    Path
        Directory containing the downloaded results.

    Raises
    ------
    RuntimeError
        If the batch job does not finish with status "finished".
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    @retry(max_attempts=max_retries, delay=retry_delay, exceptions=(Exception,))
    def _submit_and_wait():
        logger.info("Submitting batch job '%s' …", job_title)
        job = process_graph.create_job(title=job_title)
        job.start_and_wait()
        status = job.status()
        if status != "finished":
            raise RuntimeError(
                f"Batch job '{job_title}' ended with status: {status}"
            )
        logger.info("Batch job '%s' finished successfully.", job_title)
        return job

    job = _submit_and_wait()

    logger.info("Downloading results to %s …", output_dir)
    results = job.get_results()
    results.download_files(str(output_dir))
    return output_dir
