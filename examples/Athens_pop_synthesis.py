"""Generate a x% synthetic population for internal metropolitan Athens."""

from pathlib import Path
import unicodedata

import matplotlib.pyplot as plt
import pandas as pd

from polispuzzle.plan_assign import assignDiaries, printDiagnostics
from polispuzzle.pop_synthesis import (
    add_car_count,
    assign_car_count_to_agents,
    generate_agents_from_joint_distribution,
    get_ipf_seed,
    get_settlement_demographics,
    ipf,
    list_elstat_settlements,
    load_socio_mapping,
    standardize_matrix,
)

# %% Step 1. Set the input links

ZONE_FILE = Path(
    ""
) # Paste the local file links !
DIARIES_FILE = Path(
    ""
) # Paste the local file links !
SOCIO_FILE = Path(
    ""
) # Paste the local file links !
# OUTPUT_FILE = Path(__file__).with_name("Athens_population_1pct.csv")
POPULATION_PERCENTAGE = 1
RANDOM_SEED = 42

# %% Step 2. Additional functions necessary for processing
def normalized_name(value):
    """Return an accent- and case-insensitive administrative-area name."""
    text = unicodedata.normalize("NFD", str(value).strip().casefold())
    return " ".join(
        "".join(character for character in text if not unicodedata.combining(character))
        .replace("ς", "σ")
        .split()
    )

# The plotting function require serious updates.
def plotDistributions(data, title):
    """Plot home, gender and age-group distributions in separate figures."""
    columns = {
        "home": "Home",
        "gender": "Gender",
        "age_group": "Age group",
    }
    missing = set(columns) - set(data.columns)
    if missing:
        raise ValueError(f"data is missing columns: {sorted(missing)}")

    for column, label in columns.items():
        figure, axis = plt.subplots(figsize=(10, 8))
        counts = data[column].fillna("Missing").value_counts().sort_index()
        wedges, _, _ = axis.pie(
            counts,
            autopct=lambda percentage: f"{percentage:.1f}%",
            startangle=90,
            textprops={"fontsize": 8},
        )
        axis.set_title(label)
        axis.legend(
            wedges,
            counts.index.astype(str),
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            fontsize=7,
        )

        figure.suptitle(f"{title} — {label}", fontsize=14)
        figure.tight_layout()
        plt.show()

def plotModalSplit(diaries):
    """Plot the modal split across every trip in the diary table."""
    mode_columns = [
        column
        for column in diaries.columns
        if column.startswith("mode") and column[4:].isdigit()
    ]
    if not mode_columns:
        raise ValueError("diaries does not contain numbered mode columns")

    modes = diaries[mode_columns].stack().dropna()
    mode_counts = modes.value_counts().sort_index()
    if mode_counts.empty:
        raise ValueError("diaries does not contain any trip modes")

    figure, axis = plt.subplots(figsize=(10, 8))
    wedges, _, _ = axis.pie(
        mode_counts,
        autopct=lambda percentage: f"{percentage:.1f}%",
        startangle=90,
    )
    axis.legend(
        wedges,
        mode_counts.index.astype(str),
        title="Mode",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
    )
    axis.set_title("Modal split of assigned trips")
    figure.tight_layout()
    plt.show()
    return mode_counts

def plotDepartureTimes(diaries):
    """Plot all trip departure times in one-hour bins."""
    time_columns = [
        column
        for column in diaries.columns
        if column.startswith("time") and column[4:].isdigit()
    ]
    if not time_columns:
        raise ValueError("diaries does not contain numbered time columns")

    times = diaries[time_columns].stack().dropna().astype("string")
    time_parts = times.str.extract(r"^(\d{1,2}):(\d{2})$")
    hours = pd.to_numeric(time_parts[0], errors="coerce")
    minutes = pd.to_numeric(time_parts[1], errors="coerce")
    valid = hours.notna() & minutes.between(0, 59)
    departure_hours = hours[valid].mod(24) + minutes[valid] / 60
    if departure_hours.empty:
        raise ValueError("diaries does not contain valid departure times")

    figure, axis = plt.subplots(figsize=(12, 6))
    axis.hist(
        departure_hours,
        bins=range(25),
        edgecolor="black",
        rwidth=0.9,
    )
    axis.set_xticks(range(24))
    axis.set_xlim(0, 24)
    axis.set_xlabel("Departure hour")
    axis.set_ylabel("Number of trips")
    axis.set_title("Distribution of assigned trip departure times")
    axis.grid(axis="y", alpha=0.3)
    figure.tight_layout()
    plt.show()
    return departure_hours

def synthesize_settlement(settlement_code, mapping, random_seed):
    """Run the existing population-synthesis workflow for one settlement.
    See the pop_synthesis_example.py
    """
    gender_age, gender_education = get_settlement_demographics(settlement_code)
    settlement_population = gender_age.attrs["settlement_population"]
    number_of_agents = int(
        round(settlement_population * POPULATION_PERCENTAGE / 100)
    )
    if number_of_agents < 10:
        return None

    gender_age = standardize_matrix(
        gender_age, "gender", "age_group", mapping
    )
    gender_education = standardize_matrix(
        gender_education, "gender", "education", mapping
    )

    metadata = gender_age.attrs
    age_margin = gender_age.sum(axis=0)
    gender_margin = gender_age.sum(axis=1)
    education_margin = gender_education.sum(axis=0)

    age_education = ipf(
        ("age_group", "education"),
        {"age_group": age_margin, "education": education_margin},
        metadata=metadata,
        mapping=mapping,
    )

    employment_seed = get_ipf_seed(
        ("gender", "employment"),
        metadata,
        age_to_coarse=mapping["coarse_age_groups"],
    )
    employment_seed = standardize_matrix(
        employment_seed, "gender", "employment", mapping
    )
    employment_margin = employment_seed.sum(axis=0)

    age_employment = ipf(
        ("age_group", "employment"),
        {"age_group": age_margin, "employment": employment_margin},
        metadata=metadata,
        mapping=mapping,
    )
    gender_employment = ipf(
        ("gender", "employment"),
        {"gender": gender_margin, "employment": employment_margin},
        metadata=metadata,
        mapping=mapping,
    )
    education_employment = ipf(
        ("education", "employment"),
        {"education": education_margin, "employment": employment_margin},
        metadata=metadata,
        mapping=mapping,
    )

    joint_distribution = ipf(
        ("gender", "age_group", "education", "employment"),
        {
            "gender": gender_margin,
            "age_group": age_margin,
            "education": education_margin,
            "employment": employment_margin,
        },
        metadata=metadata,
        pairwise={
            ("gender", "age_group"): gender_age,
            ("gender", "education"): gender_education,
            ("age_group", "education"): age_education,
            ("age_group", "employment"): age_employment,
            ("gender", "employment"): gender_employment,
            ("education", "employment"): education_employment,
        },
        constraints="all",
    )

    agents = generate_agents_from_joint_distribution(
        joint_distribution,
        population_percentage=POPULATION_PERCENTAGE,
        random_seed=random_seed,
    )
    agents = assign_car_count_to_agents(
        agents,
        random_seed=random_seed + 1,
    )
    return add_car_count(agents, mapping)

def find_internal_ama_settlements(zones):
    """Return ELSTAT settlements belonging to the internal zones of Athens Metropolitan Area."""
    internal_units = (
        zones.loc[
            zones["Zone type"].str.strip().str.casefold().eq("internal"),
            [
                "Municipality Unit id",
                "Municipality Unit name",
                "Municipality name",
            ],
        ]
        .dropna()
        .drop_duplicates()
    )
    internal_units["municipal_unit_key"] = internal_units[
        "Municipality Unit name"
    ].map(normalized_name)
    internal_units["municipality_key"] = internal_units["Municipality name"].map(
        normalized_name
    )

    settlements = list_elstat_settlements()
    settlements = settlements[
        settlements["municipality_code"].astype(int).between(3500000, 3600000)
    ]
    # settlements = settlements[
    #     settlements["settlement_name"].map(normalized_name)
    #     != normalized_name("Βλητικός Σταθμός")
    # ]
    settlements["municipal_unit_key"] = settlements["municipal_unit_name"].map(
        normalized_name
    )
    settlements["municipality_key"] = settlements["municipality_name"].map(
        normalized_name
    )
    internal_settlements = settlements.merge(
        internal_units,
        on=["municipality_key", "municipal_unit_key"],
        how="inner",
        validate="many_to_one",
        suffixes=("_elstat", "_zones"),
    )

    matched_admin_keys = set(
        internal_settlements[
            ["municipality_key", "municipal_unit_key"]
        ].itertuples(index=False, name=None)
    )
    internal_admin_keys = internal_units[
        ["municipality_key", "municipal_unit_key"]
    ].apply(tuple, axis=1)
    unmatched_units = internal_units.loc[
        ~internal_admin_keys.isin(matched_admin_keys),
        ["Municipality name", "Municipality Unit name"],
    ]
    if not unmatched_units.empty:
        unmatched_labels = unmatched_units.apply(
            lambda row: (
                f"{row['Municipality name']} / {row['Municipality Unit name']}"
            ),
            axis=1,
        )
        raise LookupError(
            "No ELSTAT settlements were found for these municipality / "
            "municipal-unit pairs: "
            + ", ".join(sorted(unmatched_labels))
        )

    return internal_settlements.sort_values(
        ["Municipality Unit id", "settlement_code"]
    ).reset_index(drop=True)

# %% Step 3. Generate synthetic population in Athens, based on ELSTAT open-data

# it starts with the zones.
zones = pd.read_csv(ZONE_FILE, dtype={"Municipality Unit id": "string"})
internal_settlements = find_internal_ama_settlements(zones)
print(f"Selected {len(internal_settlements)} internal AMA settlements.")

mapping = load_socio_mapping()
agents = []

# It is a long process, because it runs multiple IPFs to make the synthesis
for position, settlement in internal_settlements.iterrows():
    print( # Run for each settlement in Athens area.
        f"[{position + 1}/{len(internal_settlements)}] "
        f"{settlement['settlement_name']}"
    )
    a = synthesize_settlement(
        settlement["settlement_code"],
        mapping,
        RANDOM_SEED + 2 * position,
    )
    if a is None:
        print("  Skipped: the requested percentage produces fewer than 10 agents.")
        continue
    a.insert(1, "settlement_code", settlement["settlement_code"])
    a.insert(2, "municipal_unit_code", settlement["municipal_unit_code"])
    a.insert(3, "municipal_unit_name", settlement["municipal_unit_name"])
    a.insert(4, "zone_municipal_unit_id", settlement["Municipality Unit id"])
    agents.append(a)

agents = pd.concat(agents, ignore_index=True)
agents.index = pd.RangeIndex(1, len(agents) + 1, name="pid")
# athens_population.to_csv(OUTPUT_FILE, index=True)

print(f"Generated agents: {len(agents)}")
# print(f"Saved population to: {OUTPUT_FILE}")
# print(athens_population.head())
plotDistributions(agents, "Step 3: Synthetic population distributions")


# %% Step 4. Match AMA travel diaries to the synthetic population

diaries = pd.read_csv(DIARIES_FILE, dtype={"pid": "string"})
socio = pd.read_csv(SOCIO_FILE, dtype={"pid": "string"})
diaries = diaries.merge(socio, on=["pid", "home"], how="inner", validate="one_to_one",)

agentsB, assignment_diagnostics = assignDiaries(
    agents,
    diaries,
    random_seed=RANDOM_SEED,
)
printDiagnostics(assignment_diagnostics)
plotDistributions(agentsB, "Step 4: Matched population distributions")

agentsB = agentsB.drop(columns = ['source_pid','home','match_level'])
agentsB = agentsB.rename(columns = {"source_home":"home"})

plotModalSplit(agentsB)
plotDepartureTimes(agentsB)
