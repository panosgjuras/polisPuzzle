from polispuzzle.pop_synthesis import (
    add_car_count,
    assign_car_count_to_agents,
    get_settlement_demographics,
    get_ipf_seed,
    list_elstat_settlements,
    generate_agents_from_joint_distribution,
    ipf,
    load_socio_mapping,
    standardize_matrix,
)
# %% Step 1. Select settlement and download basic data

settlements = list_elstat_settlements()
print(settlements.head())

settl = "Ναύπλιον"
code_set = "1110101010101"

# Using an exact settlement name:
gender_age, gender_education = get_settlement_demographics(settl)
# Or, preferably, an unambiguous ELSTAT settlement code:
# gender_age, age_education = get_settlement_demographics(code_set)

# %% Step 2. Standardize variable levels
mapping = load_socio_mapping()
gender_age = standardize_matrix(
    gender_age, "gender", "age_group", mapping
)
gender_education = standardize_matrix(
    gender_education, "gender", "education", mapping
)

# %% Step 3. Estimate age vs education with double-constrained IPF
# using the matrix of the municipality as seed.

metadata = gender_age.attrs
age_margin = gender_age.sum(axis=0)
gender_margin = gender_age.sum(axis=1)
education_margin = gender_education.sum(axis=0)

age_education = ipf(
    ("age_group", "education"),
    {"age_group": age_margin, "education": education_margin},
    metadata=metadata, mapping=mapping,
)

# %% Step 4. Estimate employment vs gender, employment vs age, employment vs education
# with single constrained IPF using the matrix of the muncipality as seed.

employment_seed = get_ipf_seed(
    ("gender", "employment"), metadata,
    age_to_coarse=mapping["coarse_age_groups"],
)
employment_seed = standardize_matrix(
    employment_seed, "gender", "employment", mapping
)
employment_margin = employment_seed.sum(axis=0)

# The same dimension-driven function performs all five fits.

age_employment = ipf(
    ("age_group", "employment"),
    {"age_group": age_margin, "employment": employment_margin},
    metadata=metadata, mapping=mapping,
)
gender_employment = ipf(
    ("gender", "employment"),
    {"gender": gender_margin, "employment": employment_margin},
    metadata=metadata, mapping=mapping,
)
education_employment = ipf(
    ("education", "employment"),
    {"education": education_margin, "employment": employment_margin},
    metadata=metadata, mapping=mapping,
)

# %% Step 5. Check the proportions

# matrices = {
#     "gender_age": gender_age,
#     "gender_education": gender_education,
#     "age_education": age_education,
#     "age_employment": age_employment,
#     "gender_employment": gender_employment,
#     "education_employment": education_employment,
# }

# for matrix_name, matrix in matrices.items():
#     print(f"\n{matrix_name}")
#     print(f"  total: {matrix.to_numpy().sum():.12f}")

#     margins = {
#         matrix.index.name or "index": matrix.sum(axis=1),
#         matrix.columns.name or "columns": matrix.sum(axis=0),
#     }
#     for variable, levels in margins.items():
#         print(f"  {variable}:")
#         for level, percentage in levels.items():
#             print(f"    {level}: {percentage:.12f}")

# %% Step 7. Run 4-dimmensional IPF and generate agents

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
    population_percentage=1,
    random_seed=42,
)

# %% Step 8. Add number of cars per household in each agent

agents = assign_car_count_to_agents(
    agents,
    random_seed=43,
)
agents = add_car_count(agents, mapping)
print(f"\nGenerated agents: {len(agents)}")
print(agents.head())
