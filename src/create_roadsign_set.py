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

GRID_SIZE = 200     ## GRID SIZE IN METERS
DATA_DIR_BOMEN = Path("src/data_bomen")
DATA_DIR_ROADSIGNS= Path("src/data_roadsigns/")
ROADSIGNS_DATA_PATH = DATA_DIR_ROADSIGNS / "verkeersborden_converted_coordinates.csv"
INCIDENTS_WEATHER_PATH =  DATA_DIR_ROADSIGNS / "Roadsign_incident_with_weather_data.csv"
ROADSIGN_DATA_CLEAN_PATH = DATA_DIR_ROADSIGNS / f"roadsign_geo_data_clean_{str(GRID_SIZE)}.csv"
INCIDENTS_WEATHER_GEO_PATH = DATA_DIR_ROADSIGNS / f"incidents_weather_geo_roadsigns_{GRID_SIZE}.csv"
GRID_DATA_PATH = DATA_DIR_ROADSIGNS / f"grid_enriched_roadsigns_{GRID_SIZE}.csv"
INCIDENT_DATA_PATH = DATA_DIR_BOMEN / 'Incidenten_oorspronkelijk_volledig.csv'

POSITIVE_SAMPLES_PATH = DATA_DIR_ROADSIGNS / f"positive_samples_roadsigns_{GRID_SIZE}.csv"
NEGATIVE_SAMPLES_PATH = DATA_DIR_ROADSIGNS / f"negative_samples_roadsigns_{GRID_SIZE}.csv"

ZIP_KEY = "Zipcode"
ZIP4_KEY = "Zip4"

DATE_WINDOW = 5

AMSTERDAM_BBOX = (52.26618, 4.64663, 52.475115999999994, 5.150491999999999)

# GRID PATH 200 by 200
GRIDS_200_AMSTERDAM_PATH = Path("src/final_data/grids/grids_200_amsterdam_centered.csv")

ROADSIGN_COLUMNS = [
    "ondersteuningsconstructie type",
    "grid_id",
    "hoogte onderkant bord",       
    "kijkrichting",
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

# GRIDS
grids = pd.read_csv(GRIDS_200_AMSTERDAM_PATH, sep=",", encoding="utf-8")
grids = gpd.GeoDataFrame(grids, geometry=gpd.GeoSeries.from_wkt(grids['geometry']))

# INCIDENTS
incidents = pd.read_csv(INCIDENT_DATA_PATH, sep=",", encoding="utf-8")
incidents = incidents.set_index('Incident_ID')

# ROAD SIGNS
roadsigns = pd.read_csv(ROADSIGNS_DATA_PATH, sep=",", encoding="utf-8", skipinitialspace = True)
roadsigns = roadsigns.dropna(axis=1, how='all')
columns_to_drop_indices = [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 21]
roadsigns.drop(roadsigns.columns[columns_to_drop_indices], axis=1, inplace=True)
roadsigns.rename(columns={'latitude': 'LAT', 'longitude': 'LNG'}, inplace=True)

# ROADSIGN INCIDENTS WITH WEATHER DATA
roadsign_incidents_weather = pd.read_csv(INCIDENTS_WEATHER_PATH, sep=",", encoding="utf-8")
roadsign_incidents_weather = roadsign_incidents_weather[~roadsign_incidents_weather.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

# ROADSIGN INCIDENTS WITHOUT WEATHER DATA
roadsign_incidents = incidents[incidents["Damage_Type"]=="Fence, Road signs, Scaffolding"]
roadsign_incidents = roadsign_incidents[~roadsign_incidents.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

# GEODATAFRAME ROADSIGNS
roadsigns_geo = gpd.GeoDataFrame(roadsigns, geometry=gpd.points_from_xy(roadsigns['LAT'], roadsigns['LNG']), crs="EPSG:4326")
incidents_geo = gpd.GeoDataFrame(roadsign_incidents_weather, geometry=gpd.points_from_xy(roadsign_incidents_weather['LON'], roadsign_incidents_weather['LAT']), crs="EPSG:4326")

# MAP ROADSIGNS AND INCIDENTS TO GRID IDS
roadsigns_geo = gpd.sjoin(roadsigns_geo, grids, how="left", op="within")
incidents_geo = gpd.sjoin(incidents_geo, grids, how="left", op="within")

roadsigns_geo = roadsigns_geo.rename(columns={"index_right" : "grid_id", "geometry" : "location"})
incidents_geo = incidents_geo.rename(columns={"index_right" : "grid_id", "geometry" : "location"})

# GET RID OF UNNECESSARY COLUMNS
columns_to_drop_indices = [5,7]
roadsigns_geo.drop(roadsigns_geo.columns[columns_to_drop_indices], axis=1, inplace=True)
columns = ['grid_id'] + [col for col in roadsigns_geo.columns if col != 'grid_id']
roadsigns_geo = roadsigns_geo[columns]

# ENRICH 
roadsigns_geo.iloc[:, 2] = pd.to_numeric(roadsigns_geo.iloc[:, 2], errors='coerce')
roadsigns_geo = roadsigns_geo.dropna(subset=[roadsigns_geo.columns[2]])

roadsigns_geo.iloc[:, 3] = pd.to_numeric(roadsigns_geo.iloc[:, 3], errors='coerce')
roadsigns_geo = roadsigns_geo.dropna(subset=[roadsigns_geo.columns[3]])

for i in grids.index:
    roadsigns_geo_sub = roadsigns_geo[roadsigns_geo.grid_id == i]
    if len(roadsigns_geo_sub) > 0:
        grids.at[i, "Gemiddelde hoogte onderkant bord"] = round(np.mean(roadsigns_geo_sub.iloc[:, [2]].values), 3)
        grids.at[i, "Gemiddelde kijkrichting"] = round(np.mean(roadsigns_geo_sub.iloc[:, [3]].values), 3)
        for name, count in roadsigns_geo_sub.iloc[:, [1]].value_counts().items():
            grids.at[i, "has_roadsign"] = True
            grids.at[i, name] = count
    else:
        grids.at[i, "has_roadsign"] = False
grids.fillna(0, inplace=True)

# SAVE BUILDING AND INCIDENT DATA 
roadsigns_geo.to_csv(ROADSIGN_DATA_CLEAN_PATH, sep=",", encoding="utf-8", index=False)
incidents_geo.to_csv(INCIDENTS_WEATHER_GEO_PATH, sep=",", encoding="utf-8", index=False)

# CLEAN AND SAVE GRID DATA
grids = grids.fillna(0)
grids[grids.has_roadsign == True]
grids['grid_id'] = grids.index
grids.to_csv(GRID_DATA_PATH, sep=",", encoding="utf-8", index=False)

# CREATE AND SAVE POSITIVE SAMPLES
incidents_geo.Date = pd.to_datetime(incidents_geo.Date)
incidents_geo_positive = incidents_geo[INCIDENT_COLUMNS]

grids['grid_id'] = grids.index

columns_to_drop_indices = [0,1]
grids.drop(grids.columns[columns_to_drop_indices], axis=1, inplace=True)
columns = ['grid_id'] + [col for col in grids.columns if col != 'grid_id']
grids_positive = grids[columns]

roadsigns_geo = roadsigns_geo.rename(columns={"OBJECTNUMMER" : "building_id"})
roadsigns_geo_positive = roadsigns_geo.drop(roadsigns_geo.columns[0], axis=1, inplace=True)

positive_samples = grids_positive.merge(incidents_geo_positive, on='grid_id', how='inner')
positive_samples.to_csv(POSITIVE_SAMPLES_PATH, sep=",", encoding="utf-8", index=False)

GRID_COLUMNS  =grids.columns

# CREATE AND SAVE NEGATIVE SAMPLES WITHOUT WEATHER DATA
def verify_sample(incidents, grid_id, date, window=DATE_WINDOW):
    start_date = date - pd.DateOffset(days=window)
    end_date = date + pd.DateOffset(days=window)

    incidents['Date'] = pd.to_datetime(incidents['Date'])  # Convert 'Date' column to Timestamp

    grids = incidents[(incidents['Date'] >= start_date) & (incidents['Date'] <= end_date)].values
    return False if grid_id not in grids else True

grids_with_roadsign = list(grids[grids.has_roadsign == True].grid_id.values)
negatives = positive_samples[['Date', 'Hour']]
negatives[GRID_COLUMNS] = None

for i, row in negatives.iterrows():
    random_grid = random.sample(grids_with_roadsign, 1)[0]
    while(verify_sample(incidents, random_grid, row.Date)):
        random_grid = random.sample(grids_with_roadsign, 1)[0]
    grid_data = grids[grids.grid_id == random_grid][GRID_COLUMNS].reset_index(drop=True)
    negatives.loc[i, GRID_COLUMNS] = grid_data.iloc[0]

negatives.to_csv(NEGATIVE_SAMPLES_PATH, sep=",", encoding="utf-8", index=False)