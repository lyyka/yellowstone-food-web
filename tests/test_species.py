from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_species_index_lists_yellowstone_mammals():
    res = client.get("/species")
    assert res.status_code == 200
    body = res.json()
    ids = {row["id"] for row in body["species"]}
    assert "canis-lupus" in ids
    assert body["species"][0]["observation_count"] >= body["species"][-1]["observation_count"]
    wolf = next(s for s in body["species"] if s["id"] == "canis-lupus")
    assert wolf["prey_count"] >= 1
    assert "elk" in wolf["blurb"].lower() or "prey" in wolf["blurb"].lower() or "eat" in wolf["blurb"].lower()


def test_species_dossier_is_ego_graph_for_wolf():
    res = client.get("/species/canis-lupus")
    assert res.status_code == 200
    body = res.json()
    assert body["species"]["id"] == "canis-lupus"
    prey_ids = {p["id"] for p in body["eats"]}
    assert "cervus-canadensis" in prey_ids
    node_ids = {n["id"] for n in body["graph"]["nodes"]}
    assert "canis-lupus" in node_ids
    assert "cervus-canadensis" in node_ids
    for edge in body["graph"]["edges"]:
        assert "canis-lupus" in (edge["source"], edge["target"])
