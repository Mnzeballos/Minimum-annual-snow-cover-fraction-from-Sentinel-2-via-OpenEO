"""
cli.py
------
Command-line entry point for the full glacier snow-cover pipeline.

Usage — YAML config (recommended)
----------------------------------
    glacier-snow --config config.yaml

Usage — inline flags
--------------------
    glacier-snow \
        --glacier-name  Perito_Moreno \
        --glacier-path  ./data/perito_moreno_glacier.geojson \
        --data-path     ./results \
        --mask-start    2018-02-15 \
        --mask-end      2018-03-15 \
        --ts-start      2018-02-01 \
        --ts-end        2024-06-30
"""

import argparse
import logging
from pathlib import Path

from .config import PipelineConfig, load_config
from .logging_config import setup_logging
from . import (
    connect_openeo,
    create_glacier_mask,
    raster_to_geojson,
    compute_snow_timeseries,
    run_batch_job,
    load_timeseries,
    compute_snow_fractions,
    get_yearly_minimum,
    plot_minimum_snow_cover,
)

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Glacier minimum annual snow-cover pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--config",        metavar="FILE",
                   help="Path to a YAML config file (overrides all other flags)")
    p.add_argument("--glacier-name",  help="Name used for output files")
    p.add_argument("--glacier-path",  help="Path to glacier outline GeoJSON")
    p.add_argument("--data-path",     default="./results", help="Base output directory")
    p.add_argument("--mask-start",    default="2018-02-15")
    p.add_argument("--mask-end",      default="2018-03-15")
    p.add_argument("--ts-start",      default="2018-02-01")
    p.add_argument("--ts-end",        default="2024-06-30")
    p.add_argument("--skip-mask",     action="store_true",
                   help="Skip mask creation; use --glacier-path as the outline directly")
    p.add_argument("--log-level",     default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file",      metavar="FILE",
                   help="Also write logs to this file")
    return p


def resolve_config(args: argparse.Namespace) -> PipelineConfig:
    if args.config:
        return load_config(args.config)
    cfg = load_config(None)
    if args.glacier_name:
        cfg.glacier_name = args.glacier_name
    if args.glacier_path:
        cfg.glacier_path = args.glacier_path
    cfg.data_path                 = args.data_path
    cfg.skip_mask                 = args.skip_mask
    cfg.mask.temporal_start       = args.mask_start
    cfg.mask.temporal_end         = args.mask_end
    cfg.timeseries.temporal_start = args.ts_start
    cfg.timeseries.temporal_end   = args.ts_end
    cfg.logging.level             = args.log_level
    cfg.logging.log_file          = args.log_file
    return cfg


def step_glacier_mask(conn, cfg: PipelineConfig) -> Path:
    logger.info("=== STEP 1: Glacier mask ===")
    create_glacier_mask(
        conn=conn,
        glacier_path=cfg.glacier_path,
        temporal_extent=[cfg.mask.temporal_start, cfg.mask.temporal_end],
        output_path=cfg.nc_path,
        cloud_cover_max=cfg.mask.cloud_cover_max,
    )
    return raster_to_geojson(cfg.nc_path, cfg.geojson_mask_path)


def step_snow_timeseries(conn, outline_path: Path, cfg: PipelineConfig) -> Path:
    logger.info("=== STEP 2: Snow time series ===")
    process_graph = compute_snow_timeseries(
        conn=conn,
        glacier_outline_path=outline_path,
        temporal_extent=[cfg.timeseries.temporal_start, cfg.timeseries.temporal_end],
        cloud_cover_max=cfg.timeseries.cloud_cover_max,
        ndsi_threshold=cfg.timeseries.ndsi_threshold,
    )
    return run_batch_job(
        process_graph=process_graph,
        output_dir=cfg.results_dir,
        job_title=f"snow_ts_{cfg.glacier_name}",
        max_retries=cfg.job.max_retries,
        retry_delay=cfg.job.retry_delay_seconds,
    )


def step_postprocess(results_dir: Path, cfg: PipelineConfig):
    logger.info("=== STEP 3: Post-processing ===")
    df = load_timeseries(results_dir / "timeseries.json")
    df = compute_snow_fractions(df)
    yearly_min = get_yearly_minimum(df, output_path=cfg.csv_path)
    logger.info("Yearly minimums:\n%s", yearly_min[["perc_snow"]].to_string())
    return yearly_min


def step_visualise(yearly_min, cfg: PipelineConfig) -> None:
    logger.info("=== STEP 4: Visualisation ===")
    plot_minimum_snow_cover(
        yearly_min=yearly_min,
        glacier_name=cfg.glacier_name,
        output_path=cfg.plot_path,
        show=False,
    )
    logger.info("Plot saved to %s", cfg.plot_path)


def main() -> None:
    args = build_parser().parse_args()
    cfg  = resolve_config(args)

    setup_logging(level=cfg.logging.level, log_file=cfg.logging.log_file)
    logger.info("Starting glacier snow-cover pipeline for '%s'", cfg.glacier_name)

    cfg.data_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Connecting to OpenEO …")
    conn = connect_openeo()

    if cfg.skip_mask:
        outline_path = Path(cfg.glacier_path)
        logger.info("Skipping mask creation; using outline: %s", outline_path)
    else:
        outline_path = step_glacier_mask(conn, cfg)

    results_dir  = step_snow_timeseries(conn, outline_path, cfg)
    yearly_min   = step_postprocess(results_dir, cfg)
    step_visualise(yearly_min, cfg)

    logger.info("Pipeline complete. All outputs in: %s", cfg.data_dir)


if __name__ == "__main__":
    main()
