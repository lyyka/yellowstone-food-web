import pytest

from api.graph_model import Edge, FoodWeb, Node
from api.store import reset_web


@pytest.fixture(autouse=True)
def _fresh_web():
    reset_web()
    yield
    reset_web()


@pytest.fixture
def tiny_web():
    nodes = [
        Node(id="canis-lupus", name="Canis lupus", common_name="Gray wolf", rank="species", in_region=True),
        Node(id="cervus-canadensis", name="Cervus canadensis", common_name="Elk", rank="species", in_region=True),
        Node(id="salix", name="Salix", common_name="Willow", rank="genus", in_region=False, kingdom="Plantae"),
    ]
    edges = [
        Edge(source="canis-lupus", target="cervus-canadensis", type="preysOn", n_records=12),
        Edge(source="cervus-canadensis", target="salix", type="eats", n_records=4),
    ]
    return FoodWeb(nodes={n.id: n for n in nodes}, edges=edges)
