from api.cascade import run_cascade_many
from api.scenario import apply_plan, parse_scenario_rules
from tests.test_cascade import _web


def test_removing_wolf_and_cougar_fully_releases_deer():
    result = run_cascade_many(_web(), ["canis-lupus", "puma-concolor"])
    effects = {e.node_id: e for e in result.effects}
    assert "canis-lupus" not in effects
    assert "puma-concolor" not in effects
    assert effects["odocoileus-hemionus"].delta_sign == 1
    assert effects["odocoileus-hemionus"].strength == 1.0


def test_parse_half_the_species():
    plan = parse_scenario_rules("What if 50% of the species were removed?")
    assert plan.action == "remove_fraction"
    assert plan.fraction == 0.5


def test_parse_all_predators():
    plan = parse_scenario_rules("What if all the hunters disappeared?")
    assert plan.action == "remove_guild"
    assert plan.guild == "hunters"


def test_everyone_tried_to_wolf_is_a_story_not_a_removal():
    prompt = "What if everyone tried to gray wolf"
    plan = parse_scenario_rules(prompt)
    assert plan.action == "tell"
    applied = apply_plan(_web(), plan, prompt)
    assert applied.removed_ids == []
    assert "canis-lupus" in applied.focus_ids
    web = _web()
    a = apply_plan(web, parse_scenario_rules("remove 50% of species"), "remove 50% of species")
    b = apply_plan(web, parse_scenario_rules("remove 50% of species"), "remove 50% of species")
    assert a.removed_ids == b.removed_ids
    assert len(a.removed_ids) == 2
