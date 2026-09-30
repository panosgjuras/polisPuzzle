import pandas as pd
import pytest

from polispuzzle.plan_assign import assignDiaries, printDiagnostics


def _person(home, gender, age, education, employment, cars):
    return {
        "home": home,
        "gender": gender,
        "age_group": age,
        "education": education,
        "employment": employment,
        "car_count": cars,
    }


def test_assign_diaries_uses_each_matching_level(capsys):
    agents = pd.DataFrame(
        [
            _person("S1 | U1 | M1", "male", "20-24", "E1", "active", 1),
            _person("S2 | U2 | M1", "female", "30-34", "E2", "active", 1),
            _person("S3 | U3 | M1", "male", "40-44", "E3", "inactive", 0),
            _person("S4 | U4 | M1", "female", "50-54", "E4", "retired", 2),
            _person("S5 | U5 | M1", "female", "60-64", "E5", "retired", 9),
            _person("S6 | U6 | M2", "male", "65-69", "E6", "retired", 1),
        ],
        index=pd.Index([1, 2, 3, 4, 5, 6], name="pid"),
    )
    diaries = pd.DataFrame(
        [
            {
                "pid": "d1",
                **_person("D1 | U1 | M1", "male", "20-24", "E1", "active", 1),
                "dest1": "A",
            },
            {
                "pid": "d2",
                **_person("D2 | U9 | M1", "female", "30-34", "E2", "active", 1),
                "dest1": "B",
            },
            {
                "pid": "d3",
                **_person("D3 | U9 | M1", "male", "40-44", "other", "inactive", 0),
                "dest1": "C",
            },
            {
                "pid": "d4",
                **_person("D4 | U9 | M1", "male", "50-54", "other", "retired", 2),
                "dest1": "D",
            },
            {
                "pid": "d5",
                **_person("D5 | U9 | M1", "male", "60-64", "other", "retired", 0),
                "dest1": "E",
            },
        ]
    )

    assigned, diagnostics = assignDiaries(
        agents, diaries, random_seed=42
    )

    assert assigned["pid"].tolist() == [1, 2, 3, 4, 5]
    assert assigned["home"].tolist() == agents.loc[1:5, "home"].tolist()
    assert assigned["source_pid"].tolist() == ["d1", "d2", "d3", "d4", "d5"]
    assert assigned["match_level"].tolist() == [
        "all_constraints",
        "without_municipal_unit",
        "without_municipal_unit_and_education",
        "without_municipal_unit_education_and_gender",
        "municipality_age_group_employment_only",
    ]
    assert diagnostics["count"].to_dict() == {
        "all_constraints": 1,
        "without_municipal_unit": 1,
        "without_municipal_unit_and_education": 1,
        "without_municipal_unit_education_and_gender": 1,
        "municipality_age_group_employment_only": 1,
        "not_assigned": 1,
    }
    assert diagnostics["percentage"].tolist() == pytest.approx([100 / 6] * 6)
    printDiagnostics(diagnostics)
    output = capsys.readouterr().out
    assert "For agent 6 no diary was assigned." in output
    assert "Diary assignment diagnostics:" in output


def test_assign_diaries_requires_matching_columns():
    agents = pd.DataFrame({"home": ["S | U | M"]})
    diaries = pd.DataFrame({"pid": ["d1"], "home": ["S | U | M"]})

    try:
        assignDiaries(agents, diaries)
    except ValueError as error:
        assert "agents is missing columns" in str(error)
    else:
        raise AssertionError("Expected missing agent columns to raise ValueError")
