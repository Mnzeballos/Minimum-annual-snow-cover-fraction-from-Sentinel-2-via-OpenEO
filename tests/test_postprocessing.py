"""
test_postprocessing.py
----------------------
Unit tests for glacier_snow_analysis.postprocessing.
No OpenEO connection required.
"""

import pytest
import pandas as pd

from glacier_snow_analysis.postprocessing import (
    load_timeseries,
    compute_snow_fractions,
    get_yearly_minimum,
)


class TestLoadTimeseries:
    def test_returns_dataframe(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        assert isinstance(df, pd.DataFrame)

    def test_expected_columns(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        assert set(df.columns) == {"n_catchment_vals", "n_cloud_vals", "n_snow_vals"}

    def test_index_is_datetime(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_sorted_ascending(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        assert df.index.is_monotonic_increasing

    def test_row_count(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        assert len(df) == 6

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_timeseries(tmp_path / "does_not_exist.json")


class TestComputeSnowFractions:
    def test_adds_perc_columns(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        assert "perc_cloud" in df.columns
        assert "perc_snow" in df.columns

    def test_fraction_range(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        assert df["perc_snow"].between(0, 100).all()
        assert df["perc_cloud"].between(0, 100).all()

    def test_does_not_mutate_input(self, sample_timeseries_json):
        df = load_timeseries(sample_timeseries_json)
        cols_before = set(df.columns)
        compute_snow_fractions(df)
        assert set(df.columns) == cols_before

    def test_known_value(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        # First row: 300 snow / 1000 total = 30 %
        first_snow = df["perc_snow"].iloc[0]
        assert pytest.approx(first_snow, rel=1e-3) == 30.0


class TestGetYearlyMinimum:
    def test_returns_dataframe(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        ym = get_yearly_minimum(df)
        assert isinstance(ym, pd.DataFrame)

    def test_one_row_per_year(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        ym = get_yearly_minimum(df)
        # Fixture has data for 2019, 2020, 2021
        assert len(ym) == 3

    def test_minimum_is_correct(self, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        ym = get_yearly_minimum(df)
        # 2019: rows at 300 and 800 snow → min = 30 %
        assert pytest.approx(ym["perc_snow"].iloc[0], rel=1e-3) == 30.0

    def test_csv_written(self, tmp_path, sample_timeseries_json):
        df = compute_snow_fractions(load_timeseries(sample_timeseries_json))
        csv_path = tmp_path / "out.csv"
        get_yearly_minimum(df, output_path=csv_path)
        assert csv_path.exists()
        loaded = pd.read_csv(csv_path)
        assert "perc_snow" in loaded.columns
