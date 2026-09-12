from api.nl import parse_query


def test_parses_remove_wolves():
    parsed = parse_query("What if we remove wolves?")
    assert parsed.intent == "remove"
    assert parsed.taxon_hint == "wolves"


def test_parses_who_eats():
    parsed = parse_query("Who eats elk?")
    assert parsed.intent == "predators_of"
    assert parsed.taxon_hint == "elk"


def test_parses_diet():
    parsed = parse_query("What does a coyote eat?")
    assert parsed.intent == "prey_of"
    assert "coyote" in parsed.taxon_hint
