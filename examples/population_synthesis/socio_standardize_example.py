import pandas as pd
import os
import polispuzzle.pop_synthesis as psynth
# %% Step 1: Import the dataset
path = "/Users/panosgtzouras/Desktop/datasets/csv"
city = 'Penteli'
df = pd.read_csv(os.path.join(path, "sump_surveys", f"raw_datasets/surveyDataset_raw_{city}.csv"))

# %% Step 2: Fix greek text and add pid and city
df = psynth.normalize_dataframe_text(df)
df = psynth.add_city_pid(df, city) # add pid and city, they are the main identifiers
# Save the dataset v1 to not lose pid and city
df.to_csv(os.path.join(path, "sump_surveys", f"raw_datasets/surveyDataset_raw_{city}_v1.csv"))

# %% Step 3: Import the YAML file and rename
mapping = psynth.load_socio_mapping()

df = df.rename(columns=mapping["columns"])

# %% Step 4: Standardize categorical values.
for c in ["gender", "education", "employment"]:
    if c in df.columns:
        df[c] = psynth.map_values(df[c], mapping[c])

# %% Step 5: Harmonize the age based on ELSTAT age groups and add car count data
df = psynth.harmonize_age(df, mapping)
df = psynth.add_car_count(df)

# %% Step 6. Create the socio-demo dataframe
socio_tags = ['city', 'gender', 'age_group', 'education', 'employment',
               'car_count']
socio = df[socio_tags]

# %% Step 7. Inspect the results
