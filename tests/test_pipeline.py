import sys
import urllib.error
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spatial_etl"))
import pipeline  # noqa: E402


def make_raster(path):
    data = np.full((10, 10), 100, dtype="int16")
    data[:, 5:] = 300
    with rasterio.open(
        path, "w", driver="GTiff", height=10, width=10, count=1, dtype="int16",
        crs="EPSG:4326", transform=from_origin(0, 10, 1, 1), nodata=-32768,
    ) as dst:
        dst.write(data, 1)


def make_borders(path):
    gdf = gpd.GeoDataFrame(
        {"NAME_1": ["west", "east", "tiny"]},
        geometry=[box(0, 0, 5, 10), box(5, 0, 10, 10), box(0, 0, 1, 1)],
        crs="EPSG:4326",
    )
    gdf.to_file(path, driver="GeoJSON")


def run(tmp_path):
    raster = tmp_path / "elev.tif"
    borders = tmp_path / "borders.json"
    make_raster(raster)
    make_borders(borders)
    return pipeline.transform(borders, raster_file=raster).set_index("NAME_1")


def test_mean_height_is_correct(tmp_path):
    out = run(tmp_path)
    assert out.loc["west", "mean_m"] == 100
    assert out.loc["east", "mean_m"] == 300


def test_pixel_counts(tmp_path):
    out = run(tmp_path)
    assert out.loc["west", "pixels"] == 50
    assert out.loc["east", "pixels"] == 50


def test_tiny_region_is_flagged_unreliable(tmp_path):
    out = run(tmp_path)
    assert bool(out.loc["tiny", "reliable"]) is False
    assert bool(out.loc["west", "reliable"]) is True


def test_missing_country_gives_clear_error(monkeypatch, tmp_path):
    def fake_download(url, path):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(pipeline, "DATA", tmp_path)
    monkeypatch.setattr(pipeline.urllib.request, "urlretrieve", fake_download)
    with pytest.raises(RuntimeError, match="No province-level file"):
        pipeline.extract_boundaries("ABW")
