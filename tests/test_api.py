from fastapi.testclient import TestClient

from api.main import app, load_web

client = TestClient(app)


def test_health_and_graph_include_wolf():
    health = client.get("/health").json()
    assert health["ok"] is True
    assert health["nodes"] > 10
    graph = client.get("/graph").json()
    ids = {n["id"] for n in graph["nodes"]}
    assert "canis-lupus" in ids
    assert "cervus-canadensis" in ids


def test_remove_wolves_lights_elk():
    res = client.post("/remove", json={"id": "canis-lupus"})
    assert res.status_code == 200
    body = res.json()
    effect_ids = {e["node_id"]: e for e in body["effects"]}
    assert effect_ids["cervus-canadensis"]["delta_sign"] == 1
    assert any(e["delta_sign"] == -1 for e in body["effects"])
    assert body["story"]


def test_nl_remove_wolves():
    res = client.post("/query", json={"text": "What if we remove wolves?"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "remove"
    assert body["removed"]["id"] == "canis-lupus"
    assert "cervus-canadensis" in body["highlight_node_ids"]


def test_scenario_removes_half_the_mammals():
    res = client.post("/scenario", json={"text": "What if 50% of the species were removed?"})
    assert res.status_code == 200
    body = res.json()
    assert body["plan"]["action"] == "remove_fraction"
    assert len(body["removed"]) >= 1
    assert body["story"]

