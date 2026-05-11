"""
glacier_mask.py
---------------
Build and export the glacier mask from Sentinel-2 data.
"""

from __future__ import annotations

import logging
import numpy as np
import rasterio
import fiona
import geopandas as gpd
import pandas as pd

from pathlib import Path
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from openeo.processes import lte
import openeo


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MASK_COLLECTION = "SENTINEL2_L2A"
_MASK_BANDS = ["B04", "B02", "B11"]
_MASK_CLOUD_COVER = 20
_RED_SWIR_THRESHOLD = 2.7
_BLUE_THRESHOLD = 0.095


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_glacier_outline(glacier_path: str | Path) -> gpd.GeoDataFrame:
    """
    Load a glacier outline GeoJSON and ensure datetime columns are strings
    (required for OpenEO serialisation).

    Parameters
    ----------
    glacier_path : str | Path
        Path to a GeoJSON file containing the glacier outline.

    Returns
    -------
    gpd.GeoDataFrame
    """
    gdf = gpd.read_file(str(glacier_path))
    for col in gdf.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
    return gdf


def create_glacier_mask(
    conn: openeo.Connection,
    glacier_path: str | Path,
    temporal_extent: list[str],
    output_path: str | Path,
    cloud_cover_max: int = _MASK_CLOUD_COVER,
) -> Path:
    """
    Download a glacier mask raster from Sentinel-2 using spectral thresholds
    (Red/SWIR > 2.7 and Blue > 0.095) and save it as a NetCDF file.

    Parameters
    ----------
    conn : openeo.Connection
        Authenticated OpenEO connection.
    glacier_path : str | Path
        Path to the glacier outline GeoJSON.
    temporal_extent : list[str]
        Two-element list [start_date, end_date] used to subset the data cube.
    output_path : str | Path
        Destination path for the output NetCDF file.
    cloud_cover_max : int
        Maximum allowed cloud cover percentage.

    Returns
    -------
    Path
        The path of the downloaded NetCDF file.
    """
    catchment = load_glacier_outline(glacier_path)
    bbox = catchment.bounds.iloc[0]

    spatial_extent = {
        "west": bbox[0], "east": bbox[2],
        "south": bbox[1], "north": bbox[3],
        "crs": 4326,
    }
    properties = {"eo:cloud_cover": lambda x: lte(x, cloud_cover_max)}

    s2 = conn.load_collection(
        _MASK_COLLECTION,
        spatial_extent=spatial_extent,
        bands=_MASK_BANDS,
        temporal_extent=temporal_extent,
        properties=properties,
    )

    red = s2.band("B04")
    blue = s2.band("B02")
    swir = s2.band("B11")

    glacier_mask = ((red / swir > _RED_SWIR_THRESHOLD) & (blue > _BLUE_THRESHOLD)) * 1.0
    glacier_masked = glacier_mask.mask_polygon(
        catchment["geometry"][0], replacement=1
    )

    output_path = Path(output_path)
    logger.info("Downloading glacier mask to %s …", output_path)
    glacier_masked.download(str(output_path))
    logger.info("Glacier mask saved: %s", output_path)
    return output_path


def raster_to_geojson(
    input_raster: str | Path,
    output_geojson: str | Path,
    nodata_value: float = -9999,
) -> Path:
    """
    Convert a binary glacier-mask raster (NetCDF or GeoTIFF) to a GeoJSON
    polygon file in EPSG:4326.

    Parameters
    ----------
    input_raster : str | Path
        Path to the input raster file.
    output_geojson : str | Path
        Destination path for the output GeoJSON.
    nodata_value : float
        Value used to replace NaNs before polygonising.

    Returns
    -------
    Path
        Path to the written GeoJSON file.

    Raises
    ------
    ValueError
        If no valid glacier polygons are found in the raster.
    """
    input_raster = Path(input_raster)
    output_geojson = Path(output_geojson)

    with rasterio.open(input_raster) as src:
        image = src.read(1)
        src_crs = src.crs.to_string()
        image_fixed = np.nan_to_num(image, nan=nodata_value)

        polygons = []
        for polygon, value in shapes(image_fixed, transform=src.transform):
            if value > 0 and value != nodata_value:
                geom = (
                    transform_geom(src_crs, "EPSG:4326", polygon)
                    if src_crs != "EPSG:4326"
                    else polygon
                )
                polygons.append(shape(geom))

    if not polygons:
        raise ValueError("No valid glacier polygons found in the raster.")

    merged = unary_union(polygons)
    logger.info("Merged %d polygon(s) into a single %s.", len(polygons), merged.geom_type)
    geom_type = merged.geom_type  # "Polygon" or "MultiPolygon"

    schema = {
        "properties": [("DN", "int")],
        "geometry": geom_type,
    }
    feature = {"properties": {"DN": 1}, "geometry": mapping(merged)}

    with fiona.open(
        output_geojson, "w", driver="GeoJSON", schema=schema, crs="EPSG:4326"
    ) as dst:
        dst.write(feature)

    return output_geojson
