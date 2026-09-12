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
    prompt = card["prompt"].lower()
    assert "primary subject" in prompt
    assert "flying saucer" in prompt
    assert "aliens" in prompt
    assert prompt.index("flying saucer") < prompt.index("vintage")
    assert "old faithful" not in prompt
    assert card["title"] == "Aliens attacked Yellowstone"


def test_aliens_eating_wolves_stays_imagine_and_keeps_wolves_in_the_shot():
    prompt = "What if aliens attacked Yellowstone and started eating gray wolves"
    plan = parse_scenario_rules(prompt)
    assert plan.action == "imagine"
    assert "wolves" in plan.names or "gray wolf" in plan.names or "wolf" in plan.names
    applied = apply_plan(_web(), plan, prompt)
    assert applied.removed_ids == []
    assert "canis-lupus" in applied.focus_ids
    card = plan_postcard(
        prompt,
        {"action": "imagine"},
        [],
        [],
        [],
        [{"id": "canis-lupus", "common_name": "Gray Wolf", "name": "Canis lupus"}],
    )
    text = card["prompt"].lower()
    assert "eating gray wolves" in text
    assert "gray wolf" in text
    assert "flying saucer" in text
    assert "tractor beam" in text
