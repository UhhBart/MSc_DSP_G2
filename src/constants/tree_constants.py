from pathlib import Path

DATA_DIR = Path("data_bomen")
INCIDENT_DATA_PATH = DATA_DIR / 'Incidenten_oorspronkelijk_volledig.csv'
TREE_DATA_PATH =  DATA_DIR / "BOMEN_DATA.csv"
TREE_DATA_WITH_ZIP_PATH = DATA_DIR / "BOMEN_DATA_WITH_ZIP.csv"
ZIPCODE_JSON_PATH = DATA_DIR / "zipcodes_boxes.json"

GRID_SIZE = 200     ## GRID SIZE IN METERS
TREE_DATA_CLEAN_PATH = DATA_DIR / f"tree_geo_data_clean_{str(GRID_SIZE)}.csv"
GRID_DATA_PATH = DATA_DIR / f"grid_enriched_{GRID_SIZE}.csv"
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