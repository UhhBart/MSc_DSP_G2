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
        window = 5
    
    ) -> None:
        self.window = window

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
        grids_with_trees = list(grid[grid.has_tree == True].grid_id.values)
        negatives = positives[['Date', 'Hour']]
        negatives[RF_GRID_COLUMNS] = None

        for i, row in negatives.iterrows():
            random_grid = random.sample(grids_with_trees, 1)[0]
            while(self.verify_samples(incidents, random_grid, row.Date)):
                random_grid = random.sample(grids_with_trees, 1)[0]
            grid_data = grid[grid.grid_id == random_grid][RF_GRID_COLUMNS].reset_index(drop=True)
            negatives.loc[i, RF_GRID_COLUMNS] = grid_data.iloc[0]

        return negatives
