import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import folium
import math
import datetime
import geopandas as gpd
import urllib.request
import requests
import json
import time
import openmeteo_requests
import requests_cache
from folium.plugins import MarkerCluster
from shapely.geometry import Polygon, Point
from geopy.geocoders import Nominatim
from tqdm import tqdm
from geopy.distance import geodesic
from retry_requests import retry
from shapely.wkt import loads


class GetWeather:
    def __init__(
        self,
        grid_path,
        samples_path,
        num_splits = 10,
        sleep_time = 60
    ):
        self.num_splits = num_splits
        self.sleep_time = sleep_time

        self.openmeteo = None

        self.grid_df = pd.read_csv(grid_path, sep=",", encoding="utf-8")
        self.negative_samples = pd.read_csv(samples_path, sep=",", encoding="utf-8")


    import time

    def add_weather_data(
        self,
    ):
        self.grid_df['geometry'] = self.grid_df['geometry'].apply(lambda x: loads(x))
        grids_gdf = gpd.GeoDataFrame(self.grid_df, geometry='geometry')

        grids_gdf['centroid'] = grids_gdf['geometry'].centroid
        grids_gdf['middle_lat'] = grids_gdf['centroid'].apply(lambda point: point.y)
        grids_gdf['middle_lon'] = grids_gdf['centroid'].apply(lambda point: point.x)

        negative_samples = self.negative_samples.merge(grids_gdf[['middle_lat', 'middle_lon']], left_on='grid_id', right_index=True)

        negative_samples.rename(columns={'middle_lat': 'LAT', 'middle_lon': 'LON'}, inplace=True)
        columns_order = ['Date', 'grid_id', 'LAT', 'LON'] + [col for col in negative_samples.columns if col not in ['Date', 'grid_id', 'LAT', 'LON']]
        negative_samples = negative_samples[columns_order]
        # negative_samples = negative_samples.drop('Unnamed: 0', axis=1, errors='ignore')   # necessary?
        negative_samples = negative_samples.sort_index()

        # init api connection
        self.get_api_connection()

        # split data into num_splits
        # num_splits = (len(negative_samples) // 300) + 1
        df_splits = np.array_split(negative_samples, self.num_splits)
        print(f"Splitting data in {len(df_splits)}")
        # append weather data
        splits = []
        for i, df_split in enumerate(df_splits):
            self.get_api_connection()
            start = time.time()
            print(f"Getting data for subsplit {i}, length is {len(df_split)}")
            splits.append(self.get_weather_for_sub(df_split))
            print(f"Took {time.time()-start} seconds")
            if i < len(df_splits) - 1:
                print(f"Waiting for {self.sleep_time} seconds...")
                time.sleep(self.sleep_time) 
            if i == (len(df_splits) // 2):
                print("Sleeping for an hour")
                time.sleep(3600)

        negative_samples_with_weather = pd.concat(splits, axis=0)

        return negative_samples_with_weather

    def get_api_connection(self):
        # Setup the Open-Meteo API client with cache and retry on error
        self.cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
        self.retry_session = retry(self.cache_session, retries = 5, backoff_factor = 0.2)
        self.openmeteo = openmeteo_requests.Client(session = self.retry_session)

    def get_weather_for_sub(
        self,
        df_split
    ):
        # NOTE: order of weather vars matters for retrieving correct data from API
        # TODO: check: what does api do when nothing available? NAN? and necessary to set up connection for every df split?
        weather_variables = {
            'temperature_2m': [],
            'relative_humidity_2m': [],
            'dew_point_2m': [],
            'apparent_temperature': [],
            'precipitation': [],
            'rain': [],
            'snowfall': [],
            'snow_depth': [],
            'weather_code': [],
            'pressure_msl': [],
            'surface_pressure': [],
            'cloud_cover': [],
            'cloud_cover_low': [],
            'cloud_cover_mid': [],
            'cloud_cover_high': [],
            'et0_fao_evapotranspiration': [],
            'vapour_pressure_deficit': [],
            'wind_speed_10m': [],
            'wind_speed_100m': [],
            'wind_direction_10m': [],
            'wind_direction_100m': [],
            'wind_gusts_10m': [],
            'soil_temperature_0_to_7cm': [],
            'soil_temperature_7_to_28cm': [],
            'soil_temperature_28_to_100cm': [],
            'soil_temperature_100_to_255cm': [],
            'soil_moisture_0_to_7cm': [],
            'soil_moisture_7_to_28cm': [],
            'soil_moisture_28_to_100cm': [],
            'soil_moisture_100_to_255cm': []
        }
        for i, row in df_split.iterrows():
            latitude = row['LAT']
            longitude = row['LON']
            dateStr = row['Date']
            timeStr = row['Hour']

            latitude='{:.5f}'.format(latitude)
            longitude='{:.5f}'.format(longitude)

            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": dateStr,
                "end_date": dateStr,
                "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation", "rain", "snowfall", "snow_depth", "weather_code", "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "et0_fao_evapotranspiration", "vapour_pressure_deficit", "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m", "wind_gusts_10m", "soil_temperature_0_to_7cm", "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm", "soil_temperature_100_to_255cm", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm", "soil_moisture_100_to_255cm"]
            }
            responses = self.openmeteo.weather_api(url, params=params)

            # Process first location. Add a for-loop for multiple locations or weather models
            response = responses[0]

            # Process hourly data. The order of variables needs to be the same as requested.
            hourly = response.Hourly()

            # Get data for each var
            for i, (name, var_list) in enumerate(weather_variables.items()):
                var_list.append(hourly.Variables(i).ValuesAsNumpy()[int(timeStr)])

        for name, var_list in weather_variables.items():
            df_split[name] = var_list
        
        return df_split


            
            
