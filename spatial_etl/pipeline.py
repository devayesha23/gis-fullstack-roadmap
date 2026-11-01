"""Spatial ETL: average elevation per province for any country."""
import logging
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import rasterio
from rasterstats import zonal_stats

log = logging.getLogger("etl")

DATA = Path("sample-data")
ELEVATION = DATA / "wc2.1_5m_elev.tif"
GADM_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_{code}_1.json.zip"
MIN_PIXELS = 30  # my rule of thumb: fewer pixels than this means the average is shaky


def extract_boundaries(code):
    """Download province borders for a country code like PAK, or reuse the saved copy."""
    code = code.upper()
    target = DATA / f"gadm41_{code}_1.json"
    if target.exists():
        log.info("Using saved copy: %s", target.name)
        return target

    zip_path = DATA / f"gadm41_{code}_1.json.zip"
    log.info("Downloading province borders for %s", code)
    try:
        urllib.request.urlretrieve(GADM_URL.format(code=code), zip_path)
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"No province-level file for {code} (HTTP {err.code}).") from err

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA)
    return target


def transform(boundary_file, raster_file=ELEVATION):
    """Clean the borders, measure elevation inside each one, and flag shaky numbers."""
    gdf = gpd.read_file(boundary_file)
    log.info("Loaded %d regions", len(gdf))

    # 1. Remove empty shapes and repair broken ones
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    broken = (~gdf.geometry.is_valid).sum()
    if broken:
        log.warning("Repairing %d invalid shapes", broken)
        gdf["geometry"] = gdf.geometry.make_valid()

    # 2. Make sure the borders and the picture use the same ruler
    with rasterio.open(raster_file) as src:
        if src.crs is not None and gdf.crs != src.crs:
            log.info("Reprojecting borders to %s", src.crs)
            gdf = gdf.to_crs(src.crs)

    # 3. Get the numbers
    stats = zonal_stats(gdf, str(raster_file), stats=["mean", "min", "max", "count"])

    keep = [c for c in ("GID_0", "COUNTRY", "GID_1", "NAME_1", "ENGTYPE_1") if c in gdf.columns]
    out = gdf[keep + ["geometry"]].copy()
    out["pixels"] = [s["count"] for s in stats]
    out["mean_m"] = [round(s["mean"]) if s["mean"] is not None else None for s in stats]
    out["min_m"] = [s["min"] for s in stats]
    out["max_m"] = [s["max"] for s in stats]
    out["reliable"] = out["pixels"] >= MIN_PIXELS
    return out