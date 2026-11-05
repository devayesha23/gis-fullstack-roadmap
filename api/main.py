import os
from getpass import getpass
from urllib.parse import quote_plus

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

app = FastAPI(title="Region elevation API")

from auth import router as auth_router  # noqa: E402

app.include_router(auth_router)
_engine = None


def engine():
    global _engine
    if _engine is None:
        pw = quote_plus(os.environ["PGPASSWORD"])
        _engine = create_engine(
            f"postgresql+psycopg2://postgres:{pw}@{os.environ.get('PGHOST', 'localhost')}:5432/gis_refresh"
        )
    return _engine


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/countries")
def countries():
    sql = text(
        "SELECT country_code, count(*) AS regions "
        "FROM province_elevation GROUP BY country_code ORDER BY country_code"
    )
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(sql)]


@app.get("/regions/{code}")
def regions(code: str, engtype: str | None = None):
    sql = (
        "SELECT name_1, engtype_1, pixels, mean_m, min_m, max_m, reliable, "
        "ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, 0.01))::json AS geom "
        "FROM province_elevation WHERE country_code = :code"
    )
    params = {"code": code.upper()}
    if engtype:
        sql += " AND engtype_1 = :engtype"
        params["engtype"] = engtype
    sql += " ORDER BY mean_m DESC NULLS LAST"

    with engine().connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No regions found for {code.upper()}")

    features = []
    for r in rows:
        props = {k: v for k, v in r.items() if k != "geom"}
        features.append({"type": "Feature", "geometry": r["geom"], "properties": props})
    return {"type": "FeatureCollection", "features": features}


app.mount("/map", StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True), name="map")


if __name__ == "__main__":
    import uvicorn

    if "PGPASSWORD" not in os.environ:
        os.environ["PGPASSWORD"] = getpass("Postgres password: ")
    uvicorn.run(app, host="127.0.0.1", port=8000)
