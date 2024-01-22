import streamlit as st
import numpy as np
import pandas as pd

st.title('Textual print of damage report')

trees = pd.read_csv('data_sets/BOMEN_ALL.csv', sep=';')
trees = trees.rename(columns={'LNG':'LON'})

st.dataframe(trees)

with st.sidebar:
    st.write(f'Wind Speed: {st.session_state["wind_speed"]}km/h')
    st.write(f'Wind Direction: {st.session_state["wind_direction"]}')
    st.write(f'Percipitation: {st.session_state["percipitation"]}mm')
