import pandas as pd
import os
import polispuzzle.pop_synthesis as psynth
# %% Step 1: Import the dataset
path = "/Users/panosgtzouras/Desktop/datasets/csv/dataPool" # CHANGE IT, it should be a local path
city = 'Xylokastro' # Indicate the city, the survey form
version = "v1.1" # Indicate the version to save in
df = pd.read_csv(os.path.join(path, f"raw_datasets/surveyDataset_raw_{city}.csv"))

# %% Step 2: Fix greek text and add pid and city
df = psynth.normalize_dataframe_text(df)
df = psynth.add_city_pid(df, city) # add pid and city, they are the main identifiers
# Save the dataset v1 to not lose pid and city
df.to_csv(os.path.join(path, f"raw_datasets/surveyDataset_raw_{city}_{version}.csv"))

# %% Step 3: Import the YAML file and rename
mapping = psynth.load_socio_mapping()

df = df.rename(columns=mapping["columns"])

# %% Step 4: Standardize categorical values.
for c in ["gender", "education", "employment"]:
    if c in df.columns:
        df[c] = psynth.map_values(df[c], mapping[c])

# %% Step 5: Harmonize the age based on ELSTAT age groups and add car count data
df = psynth.harmonize_age(df, mapping)
df = psynth.add_car_count(df, mapping)

# %% Step 6. Create the socio-demo dataframe
socio_tags = ['city', 'gender', 'age_group', 'education', 'employment',
               'car_count']
socio = df[socio_tags]
socio.to_csv(os.path.join(path, f"processed_datasets/socio_{city}_{version}.csv"))
# %% Step 7. Inspect the socio results NEED UPDATE

for c in socio.columns: print(socio.groupby(c).size())

# %% Step 8. Add to pool

pool_path = os.path.join(path, f"processed_datasets/socio_pool_{version}.csv")

if os.path.exists(pool_path):
    # Open the existing pool and add/update the respondents.
    pool = pd.read_csv(pool_path, index_col="pid")
    pool = psynth.write_socio_to_pool(pool, socio)

else:
    # Create the first pool for this version.
    pool = psynth.pool_pid(socio)

pool.index.name = "pid"
pool.to_csv(pool_path, index=True)