import numpy as np
import pandas as pd
from pathlib import Path
import re
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAPPING_PATH = PROJECT_ROOT / "configs" / "socio_mapping_v1.8.yaml"

def load_socio_mapping(path=MAPPING_PATH):
    """
    It load the socio_mapping yaml located in the config folder
    
    """
    with Path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def normalize_text(value):
    """Normalize whitespace while preserving Greek accents and punctuation."""
    if pd.isna(value):
        return value
    if not isinstance(value, str):
        return value
    # Also replaces non-breaking spaces from Microsoft Forms.
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()

def normalize_dataframe_text(df):
    """Normalize column names and string values."""
    result = df.copy()
    result.columns = [
        normalize_text(column)
        for column in result.columns
    ]
    for column in result.select_dtypes(include=["object", "string"]).columns:
        result[column] = result[column].map(normalize_text)
    return result

def map_values(series, mapping):
    """
    Apply a YAML dictionary while retaining values that are not listed.
    
    YAML null values become Python None.
    """
    normalized_mapping = {
        normalize_text(key): value
        for key, value in mapping.items()
    }
    
    return series.map(
        lambda value: normalized_mapping.get(value, value)
    )

def add_city_pid(df, city = 'Athens'):
    """
    It adds person id (pid) in each observation.
    It adds a column with the city from which empirical data come from
    
    pid and city are the main identifiers of a respondent
    
    """
    result = df.copy()
    result["city"] = city
    result['pid'] = np.arange(1, len(df) + 1)
    result = result.set_index("pid")
    return result

def convert_age_group(value, source_bounds, rng):
    """
    It is an age group converter. This function is required for case B1,
    SEE NEXT FUNCTION.  
    """
    
    ELSTAT_AGE_BINS = list(range(0, 76, 5)) + [np.inf] # This is the bins ELSTAT that is fully respected here
    elstat_age_groups = mapping["elstat_age_groups"]
    
    if pd.isna(value): return None

    if value in elstat_age_groups: return value

    bounds = source_bounds.get(value)

    if bounds is None: return None

    lower, upper = bounds
    upper = 100 if upper is None else upper

    sampled_age = rng.integers(lower, upper + 1)

    return pd.cut(
        [sampled_age],
        bins=ELSTAT_AGE_BINS,
        labels=elstat_age_groups,
        right=False,
    )[0]

def harmonize_age(df, mapping, random_seed=42):
    """
    This function harmonize the age data according to the ELSTAT format.
    
    It uses age groups and not ages.
    
    There 3 + 1 cases: 
        (A) exact age is available
        (B1) age group is known and written in ELSTAT format
        (B2) age group is know but not written in ELSTAT format
        (C) there are no data about age in any column

    """
    
    ELSTAT_AGE_BINS = list(range(0, 76, 5)) + [np.inf] # This is the bins ELSTAT that is fully respected here
    elstat_age_groups = mapping["elstat_age_groups"]

    has_age = "age" in df.columns
    has_group = "age_group" in df.columns

    # Case A: exact age is available.
    if has_age:
        result = df.copy()
        ages = pd.to_numeric(result["age"], errors="coerce")

        # Reject fractional, negative, or unrealistic ages.
        valid = (
            ages.eq(ages.round())
            & ages.between(0, 100)
        )

        result["age_group"] = pd.cut(
            ages.where(valid),
            bins=ELSTAT_AGE_BINS,
            labels=elstat_age_groups,
            right=False,
        )
        
        return result

    # Case B1 and B2: an age-group column is available.
    if has_group:
        # CASE B1, it follows the ELSTAT format
        if df["age_group"].dropna().isin(elstat_age_groups).all():
            return df

        # Case B2: it does not follow the ELSTAT format and requires conversion
        else:
            result = df.copy()
            result["age_group"] = result["age_group"].map(
                lambda value: convert_age_group(
                    value=value,
                    source_bounds = mapping["age_groups"],
                    rng = np.random.default_rng(random_seed),
                )
            )

        return result

    raise KeyError("Data about age is not present in the dataset.")

def add_car_count(df):
    """
    It adds data about the number of cars in each household. But, the data are assigned to one person.
    If there is not indication about the number of cars, but car ownership is known:
        the algorith adds 1 car, if car_own is yes
        and 0, if car_own is no
    """
    
    component = ["car_count_conventional", "car_count_electric"]
    result = df.copy()
    
    if "car_count" in result.columns:
        result["car_count"] = map_values(result["car_count"], 
                                     mapping["car_count"]).astype("Int64")
        return result
    
    elif all(col in result.columns for col in component):
        
        for c in component:
            result[c] = map_values(result[c], mapping[c]).fillna(0).astype("Int64")
            
        result['car_count'] = result[component[0]] + result[component[1]]
        return result
    
    elif "car_own" in df.columns:
        result['car_own'] = map_values(result['car_own'], mapping['car_own'])
        result['car_count'] = np.where(result['car_own'] == '1: yes', 1, 0)
        return result
    
    raise KeyError("Data about car ownership is not present in the dataset.")
        

# %%

import pandas as pd
import os

socio_tags = ['city', 'gender', 'age_group', 'education', 'employment',
               'car_count']


# Step 1. Import the dataset
path = "/Users/panosgtzouras/Desktop/datasets/csv"
city = 'Penteli'

df = pd.read_csv(os.path.join(path, "sump_surveys", f"raw_datasets/surveyDataset_raw_{city}.csv"))
df = normalize_dataframe_text(df)
df = add_city_pid(df, city) # add pid and city, they are the main identifiers

# Save the dataset v1 to not lose pid and city
df.to_csv(os.path.join(path, "sump_surveys", f"raw_datasets/surveyDataset_raw_{city}_v1.csv")) # Update the link

# Import the YAML file with the dictionaries, for renaming and replacing
mapping = load_socio_mapping()

# Rename the columns based on the standard format
df = df.rename(columns=mapping["columns"])

# 2. Standardize categorical values.
for c in ["gender", "education", "employment"]:
    if c in df.columns:
        df[c] = map_values(df[c], mapping[c])

# Harmonize the age based on ELSTAT age groups
df = harmonize_age(df, mapping)

df = add_car_count(df)

socio = df[socio_tags]

df2 = df[["car_count", "car_count_conventional", "car_count_electric"]]



