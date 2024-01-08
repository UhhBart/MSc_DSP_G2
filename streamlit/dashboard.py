import streamlit as st
import numpy as np
import pandas as pd
import json


st.set_page_config(layout='wide')

if 'wind_speed' not in st.session_state:
    st.session_state['wind_speed'] = 150
if 'wind_direction' not in st.session_state:
    st.session_state['wind_direction'] = 'N'
if 'percipitation' not in st.session_state:
    st.session_state['percipitation'] = 20

trees = pd.read_csv('../data_sets/BOMEN_ALL.csv', sep=';')
trees = trees.rename(columns={'LNG':'LON'})

st.title('Dashboard')

tab1, tab2, tab3 = st.tabs(['Map', 'Input', 'Textual'])

map_slice = trees.iloc[0:1000,]
focus_dict = {'All':0, 'Trees':1, 'Infrastructure':2}

with tab1:
    col1, col2 = st.columns([7,2])

    col2.write(f'Wind Speed: {st.session_state["wind_speed"]}km/h')
    col2.write(f'Wind Direction: {st.session_state["wind_direction"]}')
    col2.write(f'Percipitation: {st.session_state["percipitation"]}mm')

    focus = col2.selectbox('Select Focus', ['All', 'Trees', 'Infrastructure'])

    col1.map(trees.iloc[focus_dict[focus]*1000:(focus_dict[focus]+1)*1000,])
    col1.dataframe(trees)

with tab2:
    col1, _, col2, _, col3, _, col4 = st.columns([4, 1, 4, 1, 4, 1, 4])
    # col1
    col1.text('Create Storm')
    wind_speed = 150
    if 'wind_speed' in st.session_state:
        wind_speed = st.session_state['wind_speed']

    st.session_state['wind_speed'] = col1.slider('Set Wind Speed', 0, 250, wind_speed)

    wind_dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    wind_dir_index = 0
    if 'wind_direction' in st.session_state:
        wind_dir_index = wind_dirs.index(st.session_state['wind_direction'])

    st.session_state['wind_direction'] = col1.radio('Select Wind Direction',
                                                ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                                                index=wind_dir_index)

    percip = 20
    if 'percipitation' in st.session_state:
        percip = st.session_state['percipitation']

    st.session_state['percipitation'] = col1.number_input('Set Percipitation', 0, None, percip)

    # col2
    col2.text('Choose Storm')
    col2.radio('Previous Storms', ['Agner', 'Babet', 'Debi', 'Piet'])

    # col3
    col3.text('From Weather Forecast')
    col3.radio('Day', ['Today', 'Tomorrow', 'Overmorrow'])

    # col4
    col4.text('Upload CSV')
    col4.file_uploader('Storm Data')

with tab3:
   st.dataframe(trees, height=800)
