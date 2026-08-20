"""Population synthesis utilities for PolisPuzzle."""

from .standardize import (
    add_car_count,
    add_city_pid,
#    convert_age_group,
    harmonize_age,
    load_socio_mapping,
    map_matrix_categories,
    map_values,
    normalize_dataframe_text,
    standardize_matrix,
#    normalize_text,
)

from .socioPooling import (pool_pid, write_socio_to_pool)
from .sampleOpenElstat import (
    assign_car_count_to_agents,
    build_probability_matrix,
    generate_agents_from_joint_distribution,
    get_settlement_demographics,
    get_ipf_seed,
    ipf,
    list_elstat_settlements,
    reconcile_totals,
    run_ipf,
    validate_ipf_inputs,
)

__all__ = [
    "load_socio_mapping",
#    "normalize_text",
    "normalize_dataframe_text",
    "map_values",
    "map_matrix_categories",
    "standardize_matrix",
    "add_city_pid",
#    "convert_age_group",
    "harmonize_age",
    "add_car_count",
    "pool_pid",
    "write_socio_to_pool",
    "get_settlement_demographics",
    "ipf",
    "generate_agents_from_joint_distribution",
    "assign_car_count_to_agents",
    "list_elstat_settlements",
    "build_probability_matrix",
    "reconcile_totals",
    "get_ipf_seed",
    "run_ipf",
    "validate_ipf_inputs",
]
