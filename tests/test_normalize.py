import pytest

from api.normalize import (
    canonical_interaction,
    collapse_to_species,
    node_id_for,
    should_keep_taxon,
)


def test_canonical_interaction_collapses_inverses():
    assert canonical_interaction("preyedUponBy") == ("preysOn", True)
    assert canonical_interaction("eatenBy") == ("eats", True)
    assert canonical_interaction("preysOn") == ("preysOn", False)
    assert canonical_interaction("interactsWith") is None


def test_collapse_subspecies_to_species():
    assert collapse_to_species("Canis lupus familiaris") == "Canis familiaris"
    assert collapse_to_species("Cervus canadensis nelsoni") == "Cervus canadensis"
    assert collapse_to_species("Canis lupus") == "Canis lupus"
    assert collapse_to_species("Salix") == "Salix"


def test_drops_dogs_and_keeps_wolves():
    assert should_keep_taxon("Canis familiaris") is False
    assert should_keep_taxon("Canis lupus") is True
    assert should_keep_taxon("Homo sapiens") is False


def test_node_ids_are_stable_scientific_names():
    assert node_id_for("Canis lupus", "EOL:328607") == "canis-lupus"
    assert node_id_for("Cervus elaphus", None) == "cervus-canadensis"
