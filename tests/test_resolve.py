from api.graph_model import FoodWeb
from api.resolve import resolve_taxon


def test_resolves_common_and_scientific_names(tiny_web):
    assert resolve_taxon(tiny_web, "wolves").id == "canis-lupus"
    assert resolve_taxon(tiny_web, "Canis lupus").id == "canis-lupus"
    assert resolve_taxon(tiny_web, "elk").id == "cervus-canadensis"


def test_unknown_taxon_returns_none(tiny_web):
    assert resolve_taxon(tiny_web, "unicorn") is None
