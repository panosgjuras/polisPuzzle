"""Match observed travel diaries to synthetic agents."""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd


SOCIO_COLUMNS = ("gender", "age_group", "education", "employment", "car_count")
MATCH_LEVELS = (
    "all_constraints",
    "without_municipal_unit",
    "without_municipal_unit_and_education",
    "without_municipal_unit_education_and_gender",
    "municipality_age_group_employment_only",
)


def _normalize_location(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value).strip().casefold())
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char))
        .replace("ς", "σ")
        .split()
    )


def _add_home_areas(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    home_parts = result["home"].astype("string").str.split("|", regex=False)
    valid_home = result["home"].notna() & home_parts.str.len().ge(3)
    if not valid_home.all():
        invalid_rows = result.index[~valid_home].tolist()
        raise ValueError(
            "home must use 'settlement | municipal unit | municipality'; "
            f"invalid rows: {invalid_rows[:10]}"
        )
    result["_municipal_unit"] = home_parts.str[-2].str.strip().map(_normalize_location)
    result["_municipality"] = home_parts.str[-1].str.strip().map(_normalize_location)
    return result


def _lookup(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict[tuple, np.ndarray]:
    valid = frame.loc[:, columns].notna().all(axis=1)
    return {
        key if isinstance(key, tuple) else (key,): np.asarray(positions, dtype=int)
        for key, positions in frame.loc[valid].groupby(
            list(columns), sort=False, dropna=False
        ).groups.items()
    }


def printDiagnostics(diagnostics: pd.DataFrame) -> None:
    """Print the counts and percentages returned by :func:`assignDiaries`."""
    required = {"count", "percentage"}
    missing = required - set(diagnostics.columns)
    if missing:
        raise ValueError(f"diagnostics is missing columns: {sorted(missing)}")
    print("\nDiary assignment diagnostics:")
    print(diagnostics.loc[:, ["count", "percentage"]])


def assignDiaries(
    agents: pd.DataFrame,
    diaries: pd.DataFrame,
    *,
    random_seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Randomly assign one compatible observed diary to every possible agent.

    Both inputs must contain ``home`` in the format
    ``settlement | municipal unit | municipality`` and the five standardized
    socioeconomic columns in :data:`SOCIO_COLUMNS`. The diary table must also
    contain its observed traveller ``pid``. Candidate diaries are sampled with
    replacement and equal probability.

    Matching starts with municipality, municipal unit and all socioeconomic
    constraints. It then relaxes municipal unit, education and gender in that
    order, followed by car count. Municipality, age group and employment are
    never relaxed.

    Returns
    -------
    (pandas.DataFrame, pandas.DataFrame)
        Assigned diaries and a count/percentage diagnostic table. Assigned
        diaries use the synthetic agent pid and home; ``source_pid`` and
        ``source_home`` identify the sampled observed diary.
    """
    if not isinstance(agents, pd.DataFrame) or not isinstance(diaries, pd.DataFrame):
        raise TypeError("agents and diaries must be pandas DataFrames")

    agent_required = {"home", *SOCIO_COLUMNS}
    diary_required = {"pid", "home", *SOCIO_COLUMNS}
    missing_agents = agent_required - set(agents.columns)
    missing_diaries = diary_required - set(diaries.columns)
    if missing_agents:
        raise ValueError(f"agents is missing columns: {sorted(missing_agents)}")
    if missing_diaries:
        raise ValueError(f"diaries is missing columns: {sorted(missing_diaries)}")

    agent_work = _add_home_areas(agents)
    if "pid" in agents.columns:
        agent_work["_agent_pid"] = agents["pid"].to_numpy()
    else:
        agent_work["_agent_pid"] = agents.index.to_numpy()
    agent_work = agent_work.reset_index(drop=True)
    diary_work = _add_home_areas(diaries).reset_index(drop=True)

    # These are the basic criteria, check in the literature whether this approach is valid
    key_columns = (
        (
            "_municipality",
            "_municipal_unit",
            "gender",
            "age_group",
            "education",
            "employment",
            "car_count",
        ),
        (
            "_municipality",
            "gender",
            "age_group",
            "education",
            "employment",
            "car_count",
        ),
        (
            "_municipality",
            "gender",
            "age_group",
            "employment",
            "car_count",
        ),
        (
            "_municipality",
            "age_group",
            "employment",
            "car_count",
        ),
        (
            "_municipality",
            "age_group",
            "employment",
        ),
    )
    
    # This is the very simple method.
    lookups = [_lookup(diary_work, columns) for columns in key_columns]
    rng = np.random.default_rng(random_seed)
    counts = dict.fromkeys(MATCH_LEVELS, 0)
    counts["not_assigned"] = 0
    assigned = []

    for _, agent in agent_work.iterrows():
        selected_position = None
        selected_level = None
        for level, columns, lookup in zip(MATCH_LEVELS, key_columns, lookups):
            key = tuple(agent[column] for column in columns)
            candidates = lookup.get(key)
            if candidates is not None:
                selected_position = int(rng.choice(candidates))
                selected_level = level
                break

        agent_pid = agent["_agent_pid"]
        if selected_position is None:
            print(f"For agent {agent_pid} no diary was assigned.")
            counts["not_assigned"] += 1
            continue

        diary = diary_work.iloc[selected_position].drop(
            labels=["_municipality", "_municipal_unit"]
        ).copy()
        source_pid = diary["pid"]
        source_home = diary["home"]
        diary["pid"] = agent_pid
        diary["home"] = agent["home"]
        for column in SOCIO_COLUMNS:
            diary[column] = agent[column]
        diary["source_pid"] = source_pid
        diary["source_home"] = source_home
        diary["match_level"] = selected_level
        assigned.append(diary)
        counts[selected_level] += 1

    assigned_diaries = pd.DataFrame(assigned)
    if not assigned_diaries.empty:
        first_columns = ["pid", "home", "source_pid", "source_home", "match_level"]
        assigned_diaries = assigned_diaries[
            first_columns
            + [column for column in assigned_diaries if column not in first_columns]
        ].reset_index(drop=True)

    total_agents = len(agents)
    diagnostics = pd.DataFrame(
        {
            "count": pd.Series(counts, dtype="int64"),
            "percentage": pd.Series(
                {
                    level: (count / total_agents * 100 if total_agents else 0.0)
                    for level, count in counts.items()
                }
            ),
        }
    )
    diagnostics.index.name = "match_level"
    return assigned_diaries, diagnostics
