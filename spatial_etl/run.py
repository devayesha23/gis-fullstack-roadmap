"""Run the spatial ETL for one country, for example: python spatial_etl/run.py PAK"""
import argparse
import logging
import os
import sys
from getpass import getpass
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

import pipeline

log = logging.getLogger("etl")
TABLE = "province_elevation"


def make_engine(database, user="postgres", host="localhost", port=5432):
    """Connect to PostgreSQL. The password comes from a prompt, never from the file."""
    password = os.environ.get("PGPASSWORD") or getpass(f"Postgres password for {user}: ")
    url = f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{database}"
    return create_engine(url)


def load(table, engine, code):
    """Replace this country's rows with the new ones. All or nothing."""
    table = table.copy()
    table.columns = [c if c == "geometry" else c.lower() for c in table.columns]
    table["country_code"] = code
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT to_regclass(:name) IS NOT NULL"), {"name": f"public.{TABLE}"}
        ).scalar()
        if exists:
            conn.execute(text(f"DELETE FROM {TABLE} WHERE country_code = :c"), {"c": code})
        table.to_postgis(TABLE, conn, if_exists="append")
    log.info("Loaded %d rows for %s", len(table), code)


def check(engine, code, expected):
    """Prove the data landed correctly."""
    with engine.connect() as conn:
        rows, empty, invalid = conn.execute(
            text(
                f"SELECT count(*), "
                f"count(*) FILTER (WHERE geometry IS NULL), "
                f"count(*) FILTER (WHERE NOT ST_IsValid(geometry)) "
                f"FROM {TABLE} WHERE country_code = :c"
            ),
            {"c": code},
        ).one()
        indexes = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = :t"), {"t": TABLE}
        ).scalars().all()
    log.info("Check: %d rows (expected %d), %d empty shapes, %d invalid shapes",
             rows, expected, empty, invalid)
    log.info("Indexes on %s: %s", TABLE, ", ".join(indexes) or "none")
    if rows != expected or empty or invalid:
        raise RuntimeError("Data quality check failed, see the numbers above.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("country", help="3-letter country code, for example PAK")
    parser.add_argument("--database", default="gis_refresh")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    code = args.country.upper()
    try:
        table = pipeline.transform(pipeline.extract_boundaries(code))
        engine = make_engine(args.database)
        load(table, engine, code)
        check(engine, code, len(table))
    except RuntimeError as err:
        log.error("%s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
