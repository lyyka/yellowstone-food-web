import json

from fastapi.testclient import TestClient

from api.main import app
from api.store import reset_web


def test_admin_crud_and_csv(tmp_path, monkeypatch, tiny_web):
    dest = tmp_path / "web.json"
    dest.write_text(json.dumps(tiny_web.to_dict()))
    monkeypatch.setattr("api.store.GRAPH_PATH", dest)
    reset_web()
    client = TestClient(app)

    listed = client.get("/admin/species").json()
    assert listed["count"] == 3

    created = client.post(
        "/admin/species",
        json={
            "name": "Puma concolor",
            "common_name": "Mountain Lion",
            "kingdom": "Animalia",
            "in_region": True,
            "eats": ["Cervus canadensis"],
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["id"] == "puma-concolor"
    assert body["prey_count"] == 1

    clash = client.post("/admin/species", json={"name": "Puma concolor", "in_region": True})
    assert clash.status_code == 409

    updated = client.put(
        "/admin/species/puma-concolor",
        json={"name": "Puma concolor", "common_name": "Cougar", "in_region": True, "eats": ["Salix"]},
    )
    assert updated.status_code == 200
    assert updated.json()["common_name"] == "Cougar"

    template = client.get("/admin/species/template.csv")
    assert template.status_code == 200
    assert "Lynx canadensis" in template.text

    imported = client.post(
        "/admin/species/import",
        files={"file": ("sheet.csv", template.content, "text/csv")},
    )
    assert imported.status_code == 200
    report = imported.json()
    assert report["created"] >= 1

    gone = client.delete("/admin/species/puma-concolor")
    assert gone.status_code == 200
    assert client.get("/admin/species/puma-concolor").status_code == 404
