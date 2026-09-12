from api.postcard import plan_postcard, souvenir_title
from api.scenario import apply_plan, parse_scenario_rules
from tests.test_cascade import _web


def test_souvenir_title_strips_what_if():
    assert souvenir_title("What if aliens attacked Yellowstone") == "Aliens attacked Yellowstone"


def test_aliens_are_an_imagined_postcard_not_a_removal():
    prompt = "What if aliens attacked Yellowstone?"
    plan = parse_scenario_rules(prompt)
    assert plan.action == "imagine"
    applied = apply_plan(_web(), plan, prompt)
    assert applied.removed_ids == []


def test_postcard_scene_includes_the_visitor_premise():
    card = plan_postcard(
        "What if aliens attacked Yellowstone?",
        {"action": "imagine"},
        [],
        [],
        [],
        [],
    )
    assert "aliens" in card["prompt"].lower()
    assert "Yellowstone" in card["prompt"]
    assert card["title"] == "Aliens attacked Yellowstone"
