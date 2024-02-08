import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import geopandas as gpd
import regex as re
import json
import os
import random
from pathlib import Path
from tqdm import tqdm
from geopy.geocoders import Nominatim
from shapely.geometry import Polygon, Point

from GetWeather import GetWeather
from GetNegatives import NegativeSampler


DATA_DIR = Path("data_bomen")
FINAL_DATA_DIR = Path("final_data")
INCIDENT_DATA_PATH = DATA_DIR / 'Incidenten_oorspronkelijk_volledig.csv'
TREE_DATA_PATH =  DATA_DIR / "BOMEN_DATA.csv"
TREE_DATA_WITH_ZIP_PATH = DATA_DIR / "BOMEN_DATA_WITH_ZIP.csv"
ZIPCODE_JSON_PATH = DATA_DIR / "zipcodes_boxes.json"

GRID_SIZE = 200     ## GRID SIZE IN METERS
TREE_DATA_CLEAN_PATH = DATA_DIR / f"tree_geo_data_clean_{str(GRID_SIZE)}.csv"
GRID_DATA_PATH = DATA_DIR / f"grids_enriched_NEW.csv"
INCIDENTS_WEATHER_PATH = DATA_DIR / "incidents_weather.csv"
INCIDENTS_WEATHER_GEO_PATH = DATA_DIR / f"incidents_weather_geo_{GRID_SIZE}.csv"

POSITIVE_SAMPLES_PATH = DATA_DIR / f"positive_samples{GRID_SIZE}.csv"
NEGATIVE_SAMPLES_PATH = DATA_DIR / f"negative_samples_{GRID_SIZE}.csv"

ZIP_KEY = "Zipcode"
ZIP4_KEY = "Zip4"

DATE_WINDOW = 7

AMSTERDAM_BBOX = (52.26618, 4.64663, 52.475115999999994, 5.150491999999999)

TREE_COLUMNS = [
    "id",
    "soortnaamKort",        # andere soortnamen??
    "boomhoogte",
    "stamdiameter",
    "jaarVanAanleg",
    "typeObject",
    "standplaatsGedetailleerd",
    'SDVIEW',
    "RADIUS",
    "location",
    "grid_id",
]

TREE_NAMES = ['Fraxinus', 'Salix', 'Alnus', 'Quercus', 'Tilia', 'Acer', 'Populus', 'Betula', 'Prunus', 'Platanus', 'Malus', 'Robinia', 'Crataegus',
       'Ulmus', 'Carpinus', 'Overig', 'Onbekend']

MAP_BOOMHOOGTE = {
    'a. tot 6 m.' : "0-6",
    'b. 6 tot 9 m.': "6-9",
    'c. 9 tot 12 m.': "9-12",
    'd. 12 tot 15 m.': "12-15",
    'e. 15 tot 18 m.': "15-18",
    'f. 18 tot 24 m.': "18-25",
    'g. 24 m. en hoger': "24",
    'q. Niet van toepassing': "hQ"
}

MAP_STAMDIAMETER = {
    '0,1 tot 0,2 m.': "0.1-0.2",
    '0,2 tot 0,3 m.' : "0.2-0.3",
    '0,3 tot 0,5 m.': "0.3-0.5",
    '0,5 tot 1 m.': "0.5-1.0",
    '1,0 tot 1,5 m.': "1.0-1.5",
    '1,5 m. en grot': "1.5",
    'Onbekend': "dQ",
}

SERVICE_AREAS_OUT_OF_SCOPE = [
    "Amstelveen",
    "Aalsmeer",
    "Uithoorn"
]

RF_INCIDENT_COLUMNS = [
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

RF_TREE_COLUMNS = [
    "tree_id",
    "grid_id",
    "soortnaamKort",
    "boomhoogte",
    "stamdiameter",
    "jaarVanAanleg",
    "typeObject",
    "standplaatsGedetailleerd",
]

RF_GRID_COLUMNS = [
    "grid_id",
    "has_tree",
    "avg_height",
    "avg_diameter",
    'avg_year',
    'num_trees',
    'Fraxinus', 
    'Salix', 
    'Alnus', 
    'Quercus', 
    'Tilia', 
    'Acer',
    'Populus', 
    'Betula', 
    'Prunus', 
    'Platanus', 
    'Malus', 
    'Robinia',
    'Crataegus', 
    'Ulmus', 
    'Carpinus', 
    'Overig', 
    'Onbekend'
]



def create_grid_gdf():
    geolocator = Nominatim(user_agent="my_geocoder")

    # Get coordinates for Amsterdam
    location = geolocator.geocode("Amsterdam, Netherlands")
    amsterdam_lat, amsterdam_lon = location.latitude, location.longitude

    amsterdam_bbox = AMSTERDAM_BBOX

    # Calculate grid bounds
    lat_step = GRID_SIZE / 111000  # 1 degree of latitude is approximately 111 kilometers
    lon_step = (GRID_SIZE / 111000) / np.cos(np.radians(amsterdam_lat))  # Correct for latitude

    grid_polygons = []
    for lat in np.arange(amsterdam_bbox[0], amsterdam_bbox[2], lat_step):
        for lon in np.arange(amsterdam_bbox[1], amsterdam_bbox[3], lon_step):
            polygon = Polygon([
                (lon, lat),
                (lon + lon_step, lat),
                (lon + lon_step, lat + lat_step),
                (lon, lat + lat_step),
                (lon, lat),
            ])
            grid_polygons.append(polygon)

    grid_gdf = gpd.GeoDataFrame(geometry=grid_polygons, crs="EPSG:4326")
    return grid_gdf

def create_tree_incident_gdf(incidents_weather_df, trees, grid_gdf):
    # Filter on areas in scope
    incidents_weather_df = incidents_weather_df[~incidents_weather_df.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

    # create gdf from trees
    tree_gdf = gpd.GeoDataFrame(trees, geometry=gpd.points_from_xy(trees['LNG'], trees['LAT']), crs="EPSG:4326")
    # create gdf from indicents
    incident_gdf = gpd.GeoDataFrame(incidents_weather_df, geometry=gpd.points_from_xy(incidents_weather_df['LON'], incidents_weather_df['LAT']), crs="EPSG:4326")
    #join with grid gdf
    tree_gdf = gpd.sjoin(tree_gdf, grid_gdf, how="left", op="within")
    incident_gdf = gpd.sjoin(incident_gdf, grid_gdf, how="left", op="within")

    #clean up gdf
    tree_gdf = tree_gdf.rename(columns={"geometry" : "location"})
    incident_gdf = incident_gdf.rename(columns={"geometry" : "location"})

    return tree_gdf, incident_gdf

import plotly.express as px
def plot_spacial_data(
    grid_gdf,
    tree_gdf,
    incident_gdf,
    plot_trees = True,
    plot_incidents = True
):
    # Create a plotly figure
    fig = px.choropleth_mapbox(grid_gdf, 
                                geojson=grid_gdf.geometry.__geo_interface__, 
                                locations=grid_gdf.index,
                                mapbox_style="open-street-map",
                                zoom=11, center={"lat": AMSTERDAM_BBOX[0], "lon": AMSTERDAM_BBOX[1]},
                                opacity=0.1,
                                )

    if plot_trees:
        # Add scatter plot for tree points
        fig.add_scattermapbox(
            lat=tree_gdf.location.y,
            lon=tree_gdf.location.x,
            mode='markers',
            marker=dict(
                size=4,
                color='green',
                opacity=0.7,
            ),
            text=tree_gdf['tree_id'].astype(str),
            name='Trees'
        )
    if plot_incidents:
        # Add scatter plot for tree points
        fig.add_scattermapbox(
            lat=incident_gdf.location.y,
            lon=incident_gdf.location.x,
            mode='markers',
            marker=dict(
                size=4,
                color='red',
                opacity=0.7,
            ),
            text=incident_gdf.Incident_ID.astype(str),
            name='Incidents'
        )
    # Update the layout to make it interactive
    fig.update_layout(mapbox_style="carto-positron")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.show()


def convert_cat_to_avg(
    cat_values,
    delimeter = "-"
):
    ''' 
    Converts categorical values to means of type float
    Splits cat values on delimter, computes the mean for each cat
    Returns mean of all means of the categories
    '''
    means = []
    for cat in cat_values:
        if not isinstance(cat, str):
            continue
        if not delimeter in cat:
            continue
        vals = cat.split(delimeter)
        means.append(np.mean([float(val) for val in vals]))
    m = round(np.mean(means), 3)
    return 0 if np.isnan(m) else m


def enrich_grid_df(
    grid_gdf,
    tree_gdf
):
    for i in grid_gdf['grid_id']:
        grid_gdf.at[i, "has_tree"] = False
        tree_sub_df = tree_gdf[tree_gdf['grid_id'] == i]
        if len(tree_sub_df)>0:
            grid_gdf.at[i, "has_tree"] = True
            # Compute and add averages for height, diameter and year
            grid_gdf.at[i, "avg_height"] = convert_cat_to_avg(tree_sub_df.boomhoogte.values)
            grid_gdf.at[i, "avg_diameter"] = convert_cat_to_avg(tree_sub_df.stamdiameter.values)
            grid_gdf.at[i, "avg_year"] = round(np.mean(tree_sub_df.jaarVanAanleg.values), 3)
            # Add soortnaam counts
            for name, count in tree_sub_df.soortnaamKort.value_counts().items():
                grid_gdf.at[i, name] = count

    return grid_gdf, tree_gdf

    
def save_data(tree_gdf, incident_gdf, grid_gdf):
    # save data
    tree_gdf.to_csv(TREE_DATA_CLEAN_PATH, sep=",", encoding="utf-8", index=False)
    incident_gdf.to_csv(INCIDENTS_WEATHER_GEO_PATH, sep=",", encoding="utf-8", index=False)

    # clean and save data

    grid_gdf[RF_GRID_COLUMNS] = grid_gdf[RF_GRID_COLUMNS].fillna(value=0)

    # grid_gdf[grid_gdf.has_tree == True]
    grid_gdf.to_csv(GRID_DATA_PATH, sep=",", encoding="utf-8", index=False)

def create_save_positives(incident_gdf, tree_gdf, grid_gdf):
    # Pick necessary columns
    incident_sub_gdf = incident_gdf[RF_INCIDENT_COLUMNS]

    grid_sub_gdf = grid_gdf[RF_GRID_COLUMNS]

    tree_gdf = tree_gdf.rename(columns={"id" : "tree_id"})
    tree_sub_gdf = tree_gdf[RF_TREE_COLUMNS]
    positive_samples = grid_sub_gdf.merge(incident_sub_gdf, on='grid_id', how='inner')
    positive_samples.to_csv(POSITIVE_SAMPLES_PATH, sep=",", encoding="utf-8", index=False)
    return positive_samples

def main():
    os.chdir(Path(__file__).parent)
    # read storm_data
    incident_df = pd.read_csv(INCIDENT_DATA_PATH, sep=",", encoding="utf-8")
    # incident_df = incident_df.drop(['Unnamed: 0'], axis=1)
    incident_df = incident_df.set_index('Incident_ID')

    # create datasets
    tree_df = pd.read_csv(TREE_DATA_PATH, sep=",", encoding="utf-8")
    incidents_weather_df = pd.read_csv(INCIDENTS_WEATHER_PATH, sep=",", encoding="utf-8")
    # grid_gdf = create_grid_gdf()
    grid_df = pd.read_csv("final_data/grids/grid_final_NEW.csv", sep=",", encoding="utf-8")
    grid_df = grid_df.rename(columns={'id': 'grid_id'})
    grid_gdf = gpd.GeoDataFrame(grid_df, geometry=gpd.GeoSeries.from_wkt(grid_df['geometry']), crs="EPSG:4326")

    # Filter on areas in scope
    # Incidents weather only contains trees
    incidents_weather_df = incidents_weather_df[~incidents_weather_df.Service_Area.isin(SERVICE_AREAS_OUT_OF_SCOPE)]

    # df_tree_incidents = incident_df[incident_df["Damage_Type"]=="Tree"]

    tree_gdf, incident_gdf = create_tree_incident_gdf(incidents_weather_df=incidents_weather_df, trees=tree_df, grid_gdf=grid_gdf)

    #rename categories in new col, in place so only run once
    tree_gdf['boomhoogte'] = [MAP_BOOMHOOGTE[klasse] if not klasse is np.nan else np.nan for klasse in tree_gdf.boomhoogteklasseActueel.values]
    tree_gdf['stamdiameter'] = [MAP_STAMDIAMETER[klasse] if not klasse is np.nan else np.nan for klasse in tree_gdf.stamdiameterklasse.values]

    # get rid of unnecessary columns
    # tree_gdf = tree_gdf[RF_GRID_COLUMNS]

    grid_gdf, tree_gdf = enrich_grid_df(grid_gdf=grid_gdf, tree_gdf=tree_gdf)

    # create num trees col
    grid_gdf['num_trees'] = grid_gdf[TREE_NAMES].sum(axis=1)

    #convert to datetime
    incident_gdf.Date = pd.to_datetime(incident_gdf.Date)
    incidents_weather_df.Date = pd.to_datetime(incident_gdf.Date)

    # save data
    save_data(tree_gdf=tree_gdf, incident_gdf=incident_gdf, grid_gdf=grid_gdf)

    # sample positives
    positive_samples = create_save_positives(incident_gdf=incident_gdf, tree_gdf=tree_gdf, grid_gdf=grid_gdf)
   
    # sample negatives, set according to negative sampling type
    neg_sampler = NegativeSampler(has_column='has_tree', has_tree=False, random_dates=True, random_grid=True)
    negative_samples = neg_sampler.sample_negatives(incidents_weather_df, positive_samples, grid_gdf)

    negatives_path = f"{FINAL_DATA_DIR}/trees_new_grid_neg_samples_random.csv"
    positives_path = f"{FINAL_DATA_DIR}/trees_new_grid_pos_samples.csv"

    negative_samples.to_csv(negatives_path, sep=",", encoding="utf-8", index="False")

    weather_getter = GetWeather(grid_path=GRID_DATA_PATH, samples_path=negatives_path, sleep_time=90)  
    negative_samples = weather_getter.add_weather_data()

    negative_samples.to_csv(negatives_path, sep=",", encoding="utf-8", index="False")
    positive_samples.to_csv(positives_path, sep=",", encoding="utf-8", index="False")

if __name__ == "__main__":
    main()
