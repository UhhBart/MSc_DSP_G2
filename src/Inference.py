import pickle
import numpy
import os
import requests_cache
import openmeteo_requests
import pandas as pd
from pathlib import Path
from retry_requests import retry
from datetime import datetime, timedelta

import shap
import matplotlib.pyplot as plt
import xgboost as xgb

MODEL_DIR = Path('models/')
GRID_ENRICHED_PATH = Path('data_bomen/grid_enriched_200_new.csv')

LOCATION = ('4.890439', '52.369496')

FEATURE_COLS = {'trees': ['avg_height', 'avg_year',
                          'Fraxinus', 'Salix', 'Alnus', 'Quercus', 'Tilia', 'Acer', 'Populus', 'Betula', 'Prunus', 'Platanus', 'Malus', 'Robinia', 'Crataegus', 'Ulmus', 'Carpinus',
                          'wind_gusts_10m'],
    # 'trees': ['avg_height', 'avg_year', 'has_tree', 'num_trees',
    #                       'Fraxinus', 'Salix', 'Alnus', 'Quercus', 'Tilia', 'Acer', 'Populus',
    #                       'Betula', 'Prunus', 'Platanus', 'Malus', 'Robinia', 'Crataegus',
    #                       'Ulmus', 'Carpinus', 'Overig', 'Onbekend', 'temperature_2m', 'relative_humidity_2m', 'dew_point_2m',
    #                       'apparent_temperature', 'precipitation', 'rain', 'snowfall',
    #                       'snow_depth', 'weather_code', 'pressure_msl', 'surface_pressure',
    #                       'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m',
    #    ],
       'buildings': ['has_building', 'Gewogen Gemiddeld Bouwjaar', 'wind_gusts_10m'],

    #    'roadsigns':  ['has_roadsign', 'Gemiddelde kijkrichting', 'Gemiddelde hoogte onderkant bord',
    #                   'wind_gusts_10m', 'wind_direction_10m',
    #                   'Bouwwerk', 'Buispaal', 'Flespaal', 'Hekwerk', 'Lichtmast', 'Mast',
    #                   'Muur', 'Overig', 'Portaal', 'Scheiding', 'VRI-Mast']
       'roadsigns':  ['Gemiddelde kijkrichting', 'Gemiddelde hoogte onderkant bord',
                      'wind_gusts_10m', 'wind_direction_10m',
                      'Bouwwerk', 'Buispaal', 'Flespaal', 'Hekwerk', 'Lichtmast',
                      'Mast', 'Muur', 'Overig', 'Portaal', 'Scheiding', 'VRI-Mast']
       }

MODEL_TYPE_NAMES = {'trees': 'bomen',
                    'buildings': 'gebouwen',
                    'roadsigns': 'overige'}


class Inference():
    def __init__(
        self,
        model_name,
        model_dir = MODEL_DIR,
        model_type = 'trees',
        grid_path = GRID_ENRICHED_PATH,
    ):
        model_path = model_dir / model_name

        self.clf = self.load_model(model_path)

        self.grid_df = pd.read_csv(grid_path, sep=',', encoding='utf-8')

        self.model_type = model_type

        self.lastX = []

    def get_predictions(
        self, weather_params=None, api_dates=None
    ):
        weather_vars = {
            'temperature_2m': [10],
            'relative_humidity_2m': [80],
            'dew_point_2m': [10],
            'apparent_temperature': [10],
            'precipitation': [10],
            'rain': [10],
            'snowfall': [0],
            'snow_depth': [0],
            'weather_code': [63],
            'pressure_msl': [1000],
            'surface_pressure': [1000],
            'wind_speed_10m': [80],
            'wind_gusts_10m': [120],
            'wind_direction_10m': [120],
        }
        if weather_params:
            hours_to_predict = len(list(weather_params.values())[0])
            for param in weather_params:
                weather_vars[param] = weather_params[param]

            for name, var in weather_vars.items():
                if len(var) < hours_to_predict:
                    # Extend the list by repeating its last value
                    last_value = var[-1] if len(var) > 0 else 0  # Assuming a default value of 0 if the list is empty
                    extension = [last_value] * (hours_to_predict - len(var))
                    weather_vars[name] = var + extension
                elif len(var) > hours_to_predict:
                    # Truncate the list to the first n values
                    weather_vars[name] = var[:hours_to_predict]

        else:
            if not api_dates:
                current_time = datetime.now()
                rounded_down = current_time.replace(minute=0, second=0, microsecond=0)
                rounded_up = rounded_down + timedelta(hours=4)

                api_dates = (rounded_down, rounded_up)

            formatted_dates = (api_dates[0].strftime('%Y-%m-%dT%H:%M'), api_dates[1].strftime('%Y-%m-%dT%H:%M'))

            response = self.request_weather(weather_vars=weather_vars, api_dates=formatted_dates)
            weather_vars = self.extract_weather_vars(response=response, weather_vars=weather_vars)

            hours_to_predict = int((api_dates[1] - api_dates[0]).total_seconds() / 3600)

        pred_dict = self.make_prediction(weather_vars=weather_vars, hours_to_predict=hours_to_predict)

        return pred_dict

    def load_model(self, model_path):
        # model_path = MODEL_DIR / model_name
        with open(model_path, 'rb') as f:
            clf = pickle.load(f)
        return clf


    def request_weather(self, weather_vars, api_dates):
        # connect to API
        try:
            cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
            retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
            openmeteo = openmeteo_requests.Client(session = retry_session)
        except:
            print('API connection failed.')

        longitude = LOCATION[0]
        latitude = LOCATION[1]

        url = 'https://api.open-meteo.com/v1/forecast'
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'hourly': list(weather_vars.keys()),
            'start_hour': api_dates[0],
        	'end_hour': api_dates[1]

        }
        responses = openmeteo.weather_api(url, params=params)

        return responses[0]


    def extract_weather_vars(
        self,
        response,
        weather_vars
    ):
        hourly = response.Hourly()

        # Fetch and process the first half of the variables
        for index, (name, _) in enumerate(weather_vars.items()):
            weather_vars[name] = hourly.Variables(index).ValuesAsNumpy()

        return weather_vars

    def make_prediction(
        self,
        weather_vars,
        hours_to_predict
    ):
        self.lastX = []
        all_preds = []
        pred_dict = {}
        for grid_id in self.grid_df.grid_id:
            pred_dict[grid_id] = []

        for i in range(hours_to_predict):
            grid = self.grid_df.copy(deep=True)
            for var, values in weather_vars.items():
                grid[str(var)] = values[i]
            self.lastX = grid[FEATURE_COLS[self.model_type]]
            # if self.model_type == 'trees':
            #     preds = self.clf.predict(grid[FEATURE_COLS[self.model_type]])
            # else:
            #     preds = self.clf.predict(xgb.DMatrix(grid[FEATURE_COLS[self.model_type]]))
            preds = self.clf.predict(xgb.DMatrix(grid[FEATURE_COLS[self.model_type]]))
            for id_, pred in zip(grid['grid_id'], preds):
                pred_dict[id_].append(float(pred))
                all_preds.append(preds)

        return pred_dict

    def get_explainer_plot(self):
        explainer = shap.TreeExplainer(self.clf)
        shap_values = explainer.shap_values(self.lastX)
        # if self.model_type == 'trees':
        #     shap_values = self.clf.predict(self.grid_df[FEATURE_COLS[self.model_type]], pred_contribs=True)
        # else:
        #     shap_values = self.clf.predict(xgb.DMatrix(self.grid_df[FEATURE_COLS[self.model_type]], enable_categorical=True), pred_contribs=True)
        plot = shap.summary_plot(shap_values, self.lastX, self.get_formatted_colnames(), max_display=10)
        fig, ax = plt.gcf(), plt.gca()

        ax.set_title(f'Feature Importance - {MODEL_TYPE_NAMES[self.model_type].capitalize()} Schade', fontsize=16)
        return (fig, ax)

    def get_formatted_colnames(self):
        return [f
                .replace('_', ' ')
                .replace('has', 'heeft')
                .replace('num', 'aantal')
                .replace('avg', 'gemiddelde')
                .replace('height', 'hoogte')
                .replace('year', 'jaar')
                .replace('tree', 'bomen')
                .replace('trees', 'bomen')
                .replace('precipitation', 'neerslag')
                .replace('speed', 'snelheid')
                .replace('gusts', 'stoten')
                .replace('building', 'gebouwen')
                .capitalize()
                for f in FEATURE_COLS[self.model_type]]
