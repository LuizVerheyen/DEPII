# %% [markdown]
# ## Fetching stations with Blue Bikes

# %%
import pandas as pd
import sys
from pathlib import Path
import os

ROOT = Path().resolve().parents[1]
sys.path.append(str(ROOT))

# %% [markdown]
# ### Load train station data
def train():
    # %%
    df_stations = pd.read_csv('https://raw.githubusercontent.com/iRail/stations/refs/heads/master/stations.csv')
    # df_stations = df_stations[['URI', 'name']]

    # %% [markdown]
    # ### Load Blue Bike data

    # %%
    cwd = os.getcwd()
    data_dir = os.path.join(cwd, "data")
    if not os.path.exists(data_dir):
        data_dir = os.path.abspath(os.path.join(cwd, "..", "..", "data"))
    df_bluebike = pd.read_csv(os.path.join(data_dir, "bluebikes", "blue_bike_full_data.csv"), sep=";")
        

    # %% [markdown]
    # ### Getting stations with Blue Bikes

    # %%
    df_bluebike_station = df_bluebike[df_bluebike["Location"].str.contains("Station")]

    df_bluebike_station['StationName'] = (
        df_bluebike_station['Location']
        .str.replace(r'\s*Station.*$', '', regex=True)
        .str.strip()
    )


    manual_mapping = {
        'Beveren-Waas'     : 'Beveren',
        'Brecht'           : 'Noorderkempen',
        'Mortsel-Oude-God' : 'Mortsel-Oude God',
        'Sint-Maria-Aalter': 'Maria-Aalter',
    }

    df_bluebike_station['StationName'] = (
        df_bluebike_station['StationName']
        .replace(manual_mapping)
    )

    df_bluebike_station[df_bluebike_station['StationName'].isin(manual_mapping.values())]


    # %%
    df_bluebike_station = df_bluebike_station.drop_duplicates('StationName')

    # %% [markdown]
    # ### Keeping usefull stations data where there are Blue Bikes

    # %%
    df_merged = df_stations.merge(
        df_bluebike_station,
        left_on='name',
        right_on='StationName',
        how='inner'
    )

    
    df_usefull = df_merged[['URI', 'StationName']]

    # %%
    df_usefull['URI'] = df_usefull['URI'].str.replace('http://irail.be/stations/NMBS/', '', regex=False)

    return df_usefull


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    print(train().head(1))

