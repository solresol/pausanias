import pandas as pd

import website.main as website_main


def test_adds_phrase_translations_to_greta_variant_predictors(monkeypatch):
    calls = []

    def fake_add_phrase_translations(df, conn, client, model):
        calls.append((conn, client, model, df["phrase"].tolist()))
        translated = df.copy()
        translated["english_translation"] = translated["phrase"].map(
            {"θυγάτηρ": "daughter"}
        )
        return translated

    monkeypatch.setattr(
        website_main,
        "add_phrase_translations",
        fake_add_phrase_translations,
    )
    greta_analysis = {
        "variants": [
            {
                "predictors": pd.DataFrame(
                    [
                        {
                            "phrase": "θυγάτηρ",
                            "english_translation": "",
                            "coefficient": 2.1,
                        }
                    ]
                )
            },
            {"predictors": pd.DataFrame()},
        ]
    }

    result = website_main.add_greta_analysis_phrase_translations(
        greta_analysis,
        conn="conn",
        client="client",
        model="gpt-test",
    )

    assert calls == [("conn", "client", "gpt-test", ["θυγάτηρ"])]
    assert result["variants"][0]["predictors"].iloc[0]["english_translation"] == "daughter"
