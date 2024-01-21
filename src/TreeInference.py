import pickle
import numpy
import os
import requests_cache
import openmeteo_requests
import pandas as pd
from pathlib import Path
from retry_requests import retry

MODEL_DIR = Path("models/trees/")
GRID_ENRICHED_PATH = Path("data_bomen/grid_enriched_200_new.csv")

LOCATION = ("4.890439", "52.369496")

FEATURE_COLS = ['avg_height', 'avg_year',
       'Fraxinus', 'Salix', 'Alnus', 'Quercus', 'Tilia', 'Acer', 'Populus',
       'Betula', 'Prunus', 'Platanus', 'Malus', 'Robinia', 'Crataegus',
       'Ulmus', 'Carpinus', 'Overig', 'Onbekend', 'temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
       'apparent_temperature', 'precipitation', 'rain', 'snowfall',
       'snow_depth', 'weather_code', 'pressure_msl', 'surface_pressure',
       'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m',
       ]


class makeTreePrediction():
    def __init__(
        self,
        model_name,
        grid_path,
        hours_to_predict = 8,
        model_dir = MODEL_DIR
    ):
        model_path = model_dir / model_name

        self.clf = self.load_model(model_path)
        
        self.grid_df = pd.read_csv(grid_path, sep=",", encoding="utf-8")

        self.hours_to_predict = hours_to_predict

    def get_predictions(
        self,
    ):
        vars = {
            'temperature_2m': None,
            'relative_humidity_2m': None,
            'dew_point_2m': None,
            'apparent_temperature': None,
            'precipitation': None,
            'rain': None,
            'snowfall': None,
            'snow_depth': None,
            'weather_code': None,
            'pressure_msl': None,
            'surface_pressure': None,
            'wind_speed_10m': None,
            'wind_speed_100m': None,
            'wind_direction_10m': None,
            'wind_direction_100m': None,
            'wind_gusts_10m': None,
        }
        response = self.request_weather(vars=vars)
        weather_vars = self.extract_weather_vars(response=response, vars=vars)

        pred_dict = self.make_prediction(grid_df=self.grid_df, clf=self.clf, weather_vars=weather_vars)

        return pred_dict

    def load_model(self, model_path):
        # model_path = MODEL_DIR / model_name
        with open(model_path, "rb") as f:
            clf = pickle.load(f)
        return clf
    
    
    def request_weather(self, vars):
        # connect to API
        try:
            cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
            retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
            openmeteo = openmeteo_requests.Client(session = retry_session)
        except:
            print("API connection failed.")
            
        latitude = LOCATION[0]
        longitude = LOCATION[1]

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": list(vars.keys()),
            "forecast_days" : 1,
        }
        responses = openmeteo.weather_api(url, params=params)

        return responses[0]
    

    def extract_weather_vars(
        self,
        response,
        vars
    ):
        hourly = response.Hourly()

        # Fetch and process the first half of the variables
        for index, (name, _) in enumerate(vars.items()):
            vars[name] = hourly.Variables(index).ValuesAsNumpy()

        return vars
    
    def make_prediction(
        self,
        grid_df,
        clf,
        weather_vars
    ):
        pred_dict = {}
        for grid_id in grid_df.grid_id:
            pred_dict[grid_id] = []

        for i in range(self.hours_to_predict):
            grid = grid_df.copy()
            for var, values in weather_vars.items():
                grid[var] = values[i]
            grid['prediction'] = clf.predict(grid[FEATURE_COLS])
            for i, row in grid.iterrows():
                pred_dict[row['grid_id']].append(row['prediction'])
        return pred_dict