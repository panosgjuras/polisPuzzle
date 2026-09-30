import pandas as pd

from polispuzzle.pop_synthesis import generate_agents_from_joint_distribution


def test_generated_agents_use_full_home_path():
    joint = pd.DataFrame(
        {
            "gender": ["female"],
            "age_group": ["30-34"],
            "education": ["higher"],
            "employment": ["active"],
            "probability": [1.0],
        }
    )
    joint.attrs.update(
        settlement_name="Settlement",
        municipal_unit_name="Municipal unit",
        municipality_name="Municipality",
        settlement_population=100,
    )

    agents = generate_agents_from_joint_distribution(
        joint, population_percentage=1, random_seed=42
    )

    assert "city" not in agents.columns
    assert agents.loc[1, "home"] == "Settlement | Municipal unit | Municipality"
