import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from geopy.geocoders import Nominatim
from tqdm import tqdm
from geopy.distance import geodesic
import folium
from folium.plugins import MarkerCluster
import math
import datetime
import geopandas as gpd
import urllib.request
import requests
import json
import openmeteo_requests
import requests_cache
from shapely.geometry import Polygon, Point
from retry_requests import retry
from shapely.wkt import loads
import random 
from pathlib import Path

DATA_DIR_BOMEN = Path("src/data_bomen")
DATA_DIR_GEBOUWEN = Path("src/data_gebouwen")

INCIDENT_DATA_PATH = DATA_DIR_BOMEN / 'Incidenten_oorspronkelijk_volledig.csv'
BOUWJAAR_DATA_PATH = DATA_DIR_GEBOUWEN / 'BOUWJAAR.csv'
ZIPCODE_JSON_PATH = DATA_DIR_BOMEN / "zipcodes_boxes.json"
GRID_SIZE = 200     ## GRID SIZE IN METERS

BUILDING_DATA_CLEAN_PATH = DATA_DIR_GEBOUWEN / f"building_geo_data_clean_{str(GRID_SIZE)}.csv"
GRID_DATA_PATH = DATA_DIR_GEBOUWEN / f"grid_enriched_buildings_{GRID_SIZE}.csv"
INCIDENTS_WEATHER_PATH = DATA_DIR_GEBOUWEN / "Building_incident_with_weather_data.csv"
INCIDENTS_WEATHER_GEO_PATH = DATA_DIR_GEBOUWEN / f"incidents_weather_geo_buildings_{GRID_SIZE}.csv"

POSITIVE_SAMPLES_PATH = DATA_DIR_GEBOUWEN / f"TMP3_positive_samples_buildings_{GRID_SIZE}.csv"
NEGATIVE_SAMPLES_PATH = DATA_DIR_GEBOUWEN / f"TMP3_negative_samples_buildings_{GRID_SIZE}.csv"

ZIP_KEY = "Zipcode"
ZIP4_KEY = "Zip4"

DATE_WINDOW = 5

AMSTERDAM_BBOX = (52.26618, 4.64663, 52.475115999999994, 5.150491999999999)

# GRID PATH 200 by 200
GRIDS_200_AMSTERDAM_PATH = Path("src/final_data/grids/grids_200_amsterdam_centered.csv")

BUILDING_COLUMNS = [
    "OBJECTNUMMER",
    "grid_id",
    "Bouwjaar",       
    "WKT_LNG_LAT",
    "WKT_LAT_LNG",
    "LNG",
    "LAT"
]

SERVICE_AREAS_OUT_OF_SCOPE = [
    "Amstelveen",
    "Aalsmeer",
    "Uithoorn"
]

INCIDENT_COLUMNS = [
    "Incident_ID",
    "Service_Area",
    "grid_id",
    "Date",
    "Hour",
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "snow_depth",
    "weather_code",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_temperature_28_to_100cm",
    "soil_temperature_100_to_255cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_moisture_28_to_100cm",
    "soil_moisture_100_to_255cm",
]

GRID_COLUMNS = [
    "grid_id",
    "has_building",
    "Gemiddeld Bouwjaar",
    "Gewogen Gemiddeld Bouwjaar",
    "Voor 1860",
    "1860-1919",
    "1920-1939",
    "1940-1969",
    "1970-1985",
    "1986-2001",
    "Na 2001"
]

BUILDING_COLUMNS_MODEL = [
    "building_id",
    "Bouwjaar",
    "bouwjaar_category",     
    "WKT_LNG_LAT",
    "WKT_LAT_LNG",
    "LNG",
    "LAT"
]


# GRIDS
grids = pd.read_csv(GRIDS_200_AMSTERDAM_PATH, sep=",", encoding="utf-8")
grids = gpd.GeoDataFrame(grids, geometry=gpd.GeoSeries.from_wkt(grids['geometry']))

# INCIDENTS
incidents = pd.read_csv(INCIDENT_DATA_PATH, sep=",", encoding="utf-8")
incidents = incidents.set_index('Incident_ID')

# BUILDINGS
buildings = pd.read_csv(BOUWJAAR_DATA_PATH, sep=";", encoding="utf-8")
buildings['WKT_LNG_LAT'] = buildings['WKT_LNG_LAT'].apply(loads)
buildings['WKT_LAT_LNG'] = buildings['WKT_LAT_LNG'].apply(loads)

# BUILDING INCIDENTS WITH WEATHER DATA
building_incidents_weather = pd.read_csv(INCIDENTS_WEATHER_PATH, sep=",", encoding="utf-8")
building_incidents_weather = building_incidents_weather[~building_incidents_weather.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

# BUILDING INCIDENTS WITHOUT WEATHER DATA
building_incidents = incidents[incidents["Damage_Type"]=="Building"]
building_incidents = building_incidents[~building_incidents.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

# GEODATAFRAME BUILDINGS
buildings_geo = gpd.GeoDataFrame(buildings, geometry=gpd.points_from_xy(buildings['LNG'], buildings['LAT']), crs="EPSG:4326")
incidents_geo = gpd.GeoDataFrame(building_incidents_weather, geometry=gpd.points_from_xy(building_incidents_weather['LON'], building_incidents_weather['LAT']), crs="EPSG:4326")

# MAP BUILDINGS AND INCIDENTS TO GRID IDS
buildings_geo = gpd.sjoin(buildings_geo, grids, how="left", op="within")
incidents_geo = gpd.sjoin(incidents_geo, grids, how="left", op="within")

buildings_geo = buildings_geo.rename(columns={"index_right" : "grid_id", "geometry" : "location"})
incidents_geo = incidents_geo.rename(columns={"index_right" : "grid_id", "geometry" : "location"})

# GET RID OF UNNECESSARY COLUMNS
buildings_geo = buildings_geo[BUILDING_COLUMNS]

def map_bouwjaar_to_category(bouwjaar):
    if bouwjaar < 1860:
        return "Voor 1860"
    elif 1860 <= bouwjaar <= 1919:
        return "1860-1919"
    elif 1920 <= bouwjaar <= 1939:
        return "1920-1939"
    elif 1940 <= bouwjaar <= 1969:
        return "1940-1969"
    elif 1970 <= bouwjaar <= 1985:
        return "1970-1985"
    elif 1986 <= bouwjaar <= 2001:
        return "1986-2001"
    else:
        return "Na 2001"

# BOUWJAAR CATEGORIE MAKEN
buildings_geo['bouwjaar_category'] = buildings_geo['Bouwjaar'].apply(map_bouwjaar_to_category)
buildings_geo['area'] = buildings_geo['WKT_LAT_LNG'].apply(lambda x: x.area)

# ENRICH 
for i in grids.index:
    buildings_geo_sub = buildings_geo[buildings_geo.grid_id == i]
    if len(buildings_geo_sub) > 0:
        grids.at[i, "Gemiddeld Bouwjaar"] = round(np.mean(buildings_geo_sub.Bouwjaar.values), 3)
        weighted_avg_bouwjaar = np.average(buildings_geo_sub.Bouwjaar, weights=buildings_geo_sub.area)
        grids.at[i, "Gewogen Gemiddeld Bouwjaar"] = round(weighted_avg_bouwjaar, 3)
        for name, count in buildings_geo_sub.bouwjaar_category.value_counts().items():
            grids.at[i, "has_building"] = True
            grids.at[i, name] = count
    else:
        grids.at[i, "has_building"] = False
grids.fillna(0, inplace=True)

# SAVE BUILDING AND INCIDENT DATA 
buildings_geo.to_csv(BUILDING_DATA_CLEAN_PATH, sep=",", encoding="utf-8", index=False)
incidents_geo.to_csv(INCIDENTS_WEATHER_GEO_PATH, sep=",", encoding="utf-8", index=False)

# CLEAN AND SAVE GRID DATA
grids = grids.fillna(0)
grids[grids.has_building == True]
grids['grid_id'] = grids.index
grids.to_csv(GRID_DATA_PATH, sep=",", encoding="utf-8", index=False)

# CREATE AND SAVE POSITIVE SAMPLES
incidents_geo.Date = pd.to_datetime(incidents_geo.Date)
incidents_geo_positive = incidents_geo[INCIDENT_COLUMNS]

grids['grid_id'] = grids.index
grids_positive = grids[GRID_COLUMNS]

buildings_geo = buildings_geo.rename(columns={"OBJECTNUMMER" : "building_id"})
buildings_geo_positive = buildings_geo[BUILDING_COLUMNS_MODEL]

positive_samples = grids_positive.merge(incidents_geo_positive, on='grid_id', how='inner')
positive_samples.to_csv(POSITIVE_SAMPLES_PATH, sep=",", encoding="utf-8", index=False)

# CREATE AND SAVE NEGATIVE SAMPLES WITHOUT WEATHER DATA
def verify_sample(incidents, grid_id, date, window=DATE_WINDOW):
    start_date = date - pd.DateOffset(days=window)
    end_date = date + pd.DateOffset(days=window)

    incidents['Date'] = pd.to_datetime(incidents['Date'])  # Convert 'Date' column to Timestamp

    grids = incidents[(incidents['Date'] >= start_date) & (incidents['Date'] <= end_date)].values
    return False if grid_id not in grids else True

grids_with_building = list(grids[grids.has_building == True].grid_id.values) 
negatives = positive_samples[['Date', 'Hour']]
negatives[GRID_COLUMNS] = None

# SAMPLE RANDOM DATES +
RANDOM_START_DATE = datetime.datetime(2022, 1, 1)
RANDOM_END_DATE = datetime.datetime(2023, 12, 31)

def sample_random_dates(num_samples, start_date = RANDOM_START_DATE, end_date = RANDOM_END_DATE):
    dates = []
    hours = []

    for _ in range(num_samples):
        random_datetime = start_date + datetime.timedelta(
            days=random.randint(0, (end_date - start_date).days),   # sample from 2022-2023
            hours=random.randint(6, 22)                             # sample between 0600-2200
        )
        dates.append(random_datetime.date())
        hours.append(random_datetime.hour)

    date_df = pd.DataFrame({'Date': dates, 'Hour': hours})
    return date_df

# CUSTOMIZE 
incidents = incidents
positives = positive_samples
grid = grids
has_column = 'has_building'
has_building =  True
window=5
random_dates=True, 
random_grid=True

if random_grid:
    grids_to_sample = list(grid.grid_id.values)
else:
    grids_to_sample = list(grid[grid[has_column] == has_building].grid_id.values)

# if sample random dates
if random_dates:
    negatives = sample_random_dates(num_samples=len(positives))
else:
    negatives = positives[['Date', 'Hour']]
    
negatives[GRID_COLUMNS] = None
for i, row in negatives.iterrows():
    random_grid = random.sample(grids_to_sample, 1)[0]
    while(verify_sample(incidents, random_grid, row.Date, window)):
        random_grid = random.sample(grids_to_sample, 1)[0]
    grid_data = grid[grid.grid_id == random_grid][GRID_COLUMNS].reset_index(drop=True)
    negatives.loc[i, GRID_COLUMNS] = grid_data.iloc[0]

negatives.to_csv(NEGATIVE_SAMPLES_PATH, sep=",", encoding="utf-8", index=False)

