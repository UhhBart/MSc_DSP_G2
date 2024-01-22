import pandas as pd 
import random

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

class NegativeSampler():
    def __init__(
        self,
        has_column,
        has_tree,
        window = 5
    ):
        self.has_column = has_column
        self.window = window
        self.has_tree = has_tree

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

    def sample_negatives(
        self,
        incidents,
        positives,
        grid
    ):
        grids_to_sample = list(grid[grid[self.has_column] == self.has_tree].grid_id.values)
        negatives = positives[['Date', 'Hour']]
        negatives[RF_GRID_COLUMNS] = None
        for i, row in negatives.iterrows():
            random_grid = random.sample(grids_to_sample, 1)[0]
            while(self.verify_sample(incidents, random_grid, row.Date)):
                random_grid = random.sample(grids_to_sample, 1)[0]
            grid_data = grid[grid.grid_id == random_grid][RF_GRID_COLUMNS].reset_index(drop=True)
            negatives.loc[i, RF_GRID_COLUMNS] = grid_data.iloc[0]

        return negatives