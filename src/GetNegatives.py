import random
import datetime
import pandas as pd 

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

RANDOM_START_DATE = datetime.datetime(2022, 1, 1)
RANDOM_END_DATE = datetime.datetime(2023, 12, 31)

class NegativeSampler():
    def __init__(
        self,
        has_column,
        has_tree,
        window = 5,
        random_dates = False,       # to select random dates
        random_grid = False,        # if you do not want to specify whether a grid has trees
    ):
        self.has_column = has_column
        self.window = window
        self.has_tree = has_tree
        self.random_dates = random_dates
        self.random_grid = random_grid

    def verify_sample(
        self,
        incidents,
        grid_id,
        date,
    ):
        start_date = date - pd.DateOffset(days=self.window)
        end_date = date + pd.DateOffset(days=self.window)
        grids = incidents[(incidents['Date'] >= start_date) & (incidents['Date'] <= end_date)].values

        return False if grid_id not in grids else True

    def sample_random_dates(
        self,
        num_samples,
        start_date = RANDOM_START_DATE,
        end_date = RANDOM_END_DATE
    ):
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

    def sample_negatives(
        self,
        incidents,
        positives,
        grid
    ):
        if self.random_grid:
            grids_to_sample = list(grid.grid_id.values)
        else:
            grids_to_sample = list(grid[grid[self.has_column] == self.has_tree].grid_id.values)

        # if sample random dates
        if self.random_dates:
            negatives = self.sample_random_dates(num_samples=len(positives))
        else:
            negatives = positives[['Date', 'Hour']]
            
        negatives[RF_GRID_COLUMNS] = None
        for i, row in negatives.iterrows():
            random_grid = random.sample(grids_to_sample, 1)[0]
            while(self.verify_sample(incidents, random_grid, row.Date)):
                random_grid = random.sample(grids_to_sample, 1)[0]
            grid_data = grid[grid.grid_id == random_grid][RF_GRID_COLUMNS].reset_index(drop=True)
            negatives.loc[i, RF_GRID_COLUMNS] = grid_data.iloc[0]

        return negatives
