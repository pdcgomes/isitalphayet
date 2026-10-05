import importlib.util
import json

from lab.data import REPO_ROOT

spec = importlib.util.spec_from_file_location("export_site_data", REPO_ROOT / "experiments" / "export_site_data.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)

site = export.build()


def test_every_claim_file_is_exported_with_a_verdict_and_headline():
    assert len(site["claims"]) == len(list((REPO_ROOT / "claims").glob("*.toml")))
    for claim in site["claims"]:
        assert claim["verdict"] in ("alpha", "not_alpha")
        assert claim["headline"]


def test_story_numbers_match_the_lab_outputs():
    hype = json.loads((REPO_ROOT / "experiments" / "results" / "hype_waterfall.json").read_text())
    assert [s["final_value"] for s in site["story"]["steps"]] == [s["final_value"] for s in hype["steps"]]
    assert site["meta"]["trials"] == 13


def test_curves_line_up_with_their_dates():
    story = site["story"]
    assert len(story["buy_and_hold"]["growth_weekly"]) == len(story["weeks"])
    for s in story["steps"]:
        assert len(s["growth_weekly"]) == len(story["weeks"])


def test_ai_significance_threshold_is_consistent():
    ai = site["story"]["ai"]
    assert ai["hits"] < ai["needed_for_significance"] <= ai["calls"]


def test_one_coin_flip_per_directional_call():
    ai = site["story"]["ai"]
    assert len(ai["coin_flips"]) == ai["calls"]


def test_family_curves_share_the_story_dates():
    weeks = len(site["story"]["weeks"])
    for claim in site["claims"]:
        for family in claim.get("families", []):
            assert all(len(curve) == weeks for curve in family["growth_weekly"].values())
