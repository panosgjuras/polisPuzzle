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


def map_matrix_categories(
    matrix,
    *,
    index_mapping=None,
    columns_mapping=None,
    drop_null=True,
):
    """Map matrix row/column labels and sum labels that become identical.

    This is the matrix equivalent of :func:`map_values`. Labels mapped to YAML
    ``null`` are removed by default. DataFrame ``attrs`` are retained.
    """
    result = matrix.copy()
    attrs = matrix.attrs.copy()

    if index_mapping is not None:
        mapped_index = map_values(
            pd.Series(result.index, dtype="object"), index_mapping
        )
        result.index = pd.Index(mapped_index, name=result.index.name)
        if drop_null:
            result = result.loc[result.index.notna()]
        result = result.groupby(level=0, sort=False, dropna=drop_null).sum()

    if columns_mapping is not None:
        mapped_columns = map_values(
            pd.Series(result.columns, dtype="object"), columns_mapping
        )
        result.columns = pd.Index(mapped_columns, name=result.columns.name)
        if drop_null:
            result = result.loc[:, result.columns.notna()]
        result = result.T.groupby(level=0, sort=False, dropna=drop_null).sum().T

    result.attrs = attrs
    return result


def standardize_matrix(matrix, x_dimension, y_dimension, mapping):
    """Standardize and group both dimensions of any two-dimensional matrix.

    ``x_dimension`` identifies the rows/index and ``y_dimension`` identifies
    the columns. Dimension names may already be canonical (for example,
    ``"gender"``) or may be source labels present in ``mapping["columns"]``.
    Category mappings are read from ``mapping[dimension]`` or, when present,
    ``mapping[f"{dimension}_values"]``. Categories that map to the same label
    are summed and categories mapped to YAML ``null`` are removed.
    """
    if not isinstance(matrix, pd.DataFrame):
        raise TypeError("matrix must be a pandas DataFrame")
    if not isinstance(x_dimension, str) or not isinstance(y_dimension, str):
        raise TypeError("x_dimension and y_dimension must be strings")

    column_mapping = mapping.get("columns", {})
    dimensions = map_values(
        pd.Series([x_dimension, y_dimension], dtype="object"),
        column_mapping,
    )
    x_name, y_name = dimensions.iloc[0], dimensions.iloc[1]
    if not isinstance(x_name, str) or not isinstance(y_name, str):
        raise ValueError("x_dimension and y_dimension must map to valid names")

    def category_mapping(dimension):
        values_mapping = mapping.get(f"{dimension}_values")
        if values_mapping is not None:
            return values_mapping
        direct_mapping = mapping.get(dimension, {})
        return direct_mapping if isinstance(direct_mapping, dict) else {}

    result = map_matrix_categories(
        matrix,
        index_mapping=category_mapping(x_name),
        columns_mapping=category_mapping(y_name),
    )
    result.index.name = x_name
    result.columns.name = y_name
    return result

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


ELSTAT_AGE_BINS = list(range(0, 76, 5)) + [np.inf]

def convert_age_group(
    value,
    age_groups,
    age_bins,
    source_bounds,
    rng,
):
    """Convert one non-ELSTAT age group to an ELSTAT age group."""

    if pd.isna(value):
        return pd.NA

    normalized_value = normalize_text(value)

    # Preserve an existing ELSTAT group.
    elstat_lookup = {
        normalize_text(group): group
        for group in age_groups
    }

    if normalized_value in elstat_lookup:
        return elstat_lookup[normalized_value]

    bounds = source_bounds.get(normalized_value)

    if bounds is None:
        return pd.NA

    lower, upper = bounds
    upper = 100 if upper is None else upper

    sampled_age = rng.integers(lower, upper + 1)

    return pd.cut(
        [sampled_age],
        bins=age_bins,
        labels=age_groups,
        right=False,
    )[0]

def harmonize_age(df, mapping, random_seed=42):
    """
    Harmonize age information using ELSTAT age groups.

    Cases:
        A:  Exact age is available.
        B1: age_group already follows ELSTAT.
        B2: age_group uses different group boundaries.
        C:  No age information is available.
    """
    elstat_age_groups = mapping["elstat_age_groups"]

    has_age = "age" in df.columns
    has_group = "age_group" in df.columns

    # Case A: exact age is available.
    if has_age:
        result = df.copy()
        ages = pd.to_numeric(result["age"], errors="coerce")

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

    if has_group:
        normalized_elstat_groups = {
            normalize_text(group)
            for group in elstat_age_groups
        }

        normalized_values = (
            df["age_group"]
            .dropna()
            .map(normalize_text)
        )

        # Case B1: values already follow ELSTAT.
        if normalized_values.isin(normalized_elstat_groups).all():
            return df

        # Case B2: convert source age groups.
        result = df.copy()

        # Create the generator once, not once per row.
        rng = np.random.default_rng(random_seed)

        # Normalize the YAML keys once.
        source_bounds = {
            normalize_text(key): bounds
            for key, bounds in mapping["age_groups"].items()
        }

        # object conversion guarantees row-by-row mapping when the
        # original Series has categorical dtype.
        result["age_group"] = (
            result["age_group"]
            .astype("object")
            .map(
                lambda value: convert_age_group(
                    value=value,
                    age_groups=elstat_age_groups,
                    age_bins=ELSTAT_AGE_BINS,
                    source_bounds=source_bounds,
                    rng=rng,
                )
            )
        )

        return result

    # Case C
    raise KeyError(
        "Neither 'age' nor 'age_group' is present in the dataset."
    )


def add_car_count(df, mapping):
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
