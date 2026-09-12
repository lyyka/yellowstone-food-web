import pytest

from api.cascade import run_cascade
from api.graph_model import FoodWeb, Edge, Node


def _web() -> FoodWeb:
    nodes = [
        Node(id="canis-lupus", name="Canis lupus", common_name="Gray wolf", rank="species", in_region=True),
        Node(id="cervus-canadensis", name="Cervus canadensis", common_name="Elk", rank="species", in_region=True),
        Node(id="odocoileus-hemionus", name="Odocoileus hemionus", common_name="Mule deer", rank="species", in_region=True),
        Node(id="salix", name="Salix", common_name="Willow", rank="genus", in_region=False, kingdom="Plantae"),
        Node(id="populus-tremuloides", name="Populus tremuloides", common_name="Quaking aspen", rank="species", in_region=False, kingdom="Plantae"),
        Node(id="puma-concolor", name="Puma concolor", common_name="Cougar", rank="species", in_region=True),
    ]
    edges = [
        Edge(source="canis-lupus", target="cervus-canadensis", type="preysOn", n_records=12),
        Edge(source="canis-lupus", target="odocoileus-hemionus", type="preysOn", n_records=8),
        Edge(source="puma-concolor", target="odocoileus-hemionus", type="preysOn", n_records=5),
        Edge(source="cervus-canadensis", target="salix", type="eats", n_records=4),
        Edge(source="cervus-canadensis", target="populus-tremuloides", type="eats", n_records=3),
    ]
    return FoodWeb(nodes={n.id: n for n in nodes}, edges=edges)


def test_removing_wolf_releases_elk_and_pressures_plants():
    result = run_cascade(_web(), "canis-lupus")
    effects = {e.node_id: e for e in result.effects}

    assert effects["cervus-canadensis"].delta_sign == 1
    assert effects["cervus-canadensis"].depth == 1
    assert effects["salix"].delta_sign == -1
    assert effects["salix"].depth == 2
    assert effects["populus-tremuloides"].delta_sign == -1
    assert "canis-lupus" not in effects


def test_singleton_prey_lights_up_more_than_shared_prey():
    result = run_cascade(_web(), "canis-lupus")
    effects = {e.node_id: e for e in result.effects}
    assert effects["cervus-canadensis"].strength > effects["odocoileus-hemionus"].strength


def test_story_mentions_two_hops():
    result = run_cascade(_web(), "canis-lupus")
    text = " ".join(result.story).lower()
    assert "wolf" in text or "canis lupus" in text
    assert "elk" in text
    assert "willow" in text or "aspen" in text or "plant" in text


def test_unknown_species_raises():
    with pytest.raises(KeyError):
        run_cascade(_web(), "missing")
