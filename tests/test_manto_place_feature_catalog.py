import pandas as pd

from manto_place_feature_catalog import FEATURE_BY_NAME, FEATURE_CATALOG
from predict_place_survival import CONNECTEDNESS_FEATURE_COLUMNS
from website.data import build_place_survival_feature_details


def test_feature_catalog_covers_all_connectedness_features_once():
    names = [feature.name for feature in FEATURE_CATALOG]
    slugs = [feature.slug for feature in FEATURE_CATALOG]

    assert len(names) == 41
    assert len(set(names)) == 41
    assert len(set(slugs)) == 41
    assert set(names) == set(CONNECTEDNESS_FEATURE_COLUMNS)
    assert set(FEATURE_BY_NAME) == set(names)

    for feature in FEATURE_CATALOG:
        assert feature.title
        assert feature.category
        assert feature.definition
        assert feature.calculation
        assert feature.higher_value
        assert feature.caution
        assert set(feature.related_features) <= set(names)


def test_feature_details_include_distributions_examples_and_sentinel_counts():
    rows = []
    for index, (place, target) in enumerate(
        [
            ("Athens", "survives"),
            ("Thebes", "survives"),
            ("Brenthe", "does_not_survive"),
        ],
        start=1,
    ):
        row = {
            "manto_id": f"p{index}",
            "place_label": place,
            "target_label": target,
        }
        row.update({name: 0.0 for name in CONNECTEDNESS_FEATURE_COLUMNS})
        rows.append(row)

    rows[0]["kin_linked_neighbor_count"] = 5
    rows[1]["kin_linked_neighbor_count"] = 2
    rows[2]["kin_linked_neighbor_count"] = 0
    rows[0]["earliest_attestation_year"] = -700
    rows[1]["earliest_attestation_year"] = -400
    rows[2]["earliest_attestation_year"] = 200
    cohort = pd.DataFrame(rows)
    scores = [
        {
            "feature_name": "kin_linked_neighbor_count",
            "coefficient": -1.275,
            "direction": "does_not_survive",
        }
    ]

    details = build_place_survival_feature_details(scores, cohort)
    detail_by_name = {detail["name"]: detail for detail in details}
    kin = detail_by_name["kin_linked_neighbor_count"]
    earliest = detail_by_name["earliest_attestation_year"]

    assert len(details) == 41
    assert kin["coefficient"]["coefficient"] == -1.275
    assert kin["distributions"]["overall"]["median"] == 2.0
    assert kin["high_examples"][0]["place_label"] == "Athens"
    assert kin["low_examples"][0]["place_label"] == "Brenthe"
    assert earliest["missing_count"] == 1
    assert earliest["missing_examples"][0]["place_label"] == "Brenthe"
    assert earliest["distributions"]["overall"]["count"] == 2
