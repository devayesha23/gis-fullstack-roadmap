import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import main  # noqa: E402

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}

REGIONS = {
    "PAK": [
        {"name_1": "Punjab", "engtype_1": "Province", "pixels": 2794,
         "mean_m": 225, "min_m": 74.0, "max_m": 1845.0, "reliable": True, "geom": SQUARE},
        {"name_1": "Islamabad", "engtype_1": "CapitalTerritory", "pixels": 11,
         "mean_m": 599, "min_m": 465.0, "max_m": 1066.0, "reliable": False, "geom": SQUARE},
    ]
}
COUNTRIES = [{"country_code": "PAK", "regions": 2}]


class Row:
    def __init__(self, data):
        self._mapping = data


class Result:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(Row(r) for r in self.rows)

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        if "GROUP BY country_code" in str(sql):
            return Result(COUNTRIES)
        rows = REGIONS.get(params["code"], [])
        if "engtype" in params:
            rows = [r for r in rows if r["engtype_1"] == params["engtype"]]
        return Result(rows)


class FakeEngine:
    def connect(self):
        return FakeConn()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(main, "engine", lambda: FakeEngine())
    return TestClient(main.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_countries(client):
    r = client.get("/countries")
    assert r.status_code == 200
    assert r.json() == [{"country_code": "PAK", "regions": 2}]


def test_regions_returns_geojson(client):
    r = client.get("/regions/PAK")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2
    first = body["features"][0]
    assert first["geometry"]["type"] == "Polygon"
    assert "geom" not in first["properties"]
    assert first["properties"]["name_1"] == "Punjab"


def test_country_code_is_case_insensitive(client):
    assert client.get("/regions/pak").status_code == 200


def test_engtype_filter(client):
    r = client.get("/regions/PAK?engtype=Province")
    names = [f["properties"]["name_1"] for f in r.json()["features"]]
    assert names == ["Punjab"]


def test_unknown_country_gives_404(client):
    r = client.get("/regions/ABW")
    assert r.status_code == 404
    assert "No regions found" in r.json()["detail"]


def test_map_page_is_served(client):
    r = client.get("/map/")
    assert r.status_code == 200
    assert "maplibre" in r.text.lower()
