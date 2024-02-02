def make_dashboard():
    import sys
    sys.path.append('../src')

    import streamlit as st
    import my_modal
    import numpy as np
    import pandas as pd
    import json
    import cv2
    import base64
    from itertools import groupby
    import pdfkit as pdf
    import datetime
    import pathlib
    import datetime
    import matplotlib.pyplot as plt

    from component import map_component
    from Inference import Inference
    from GetPOI import GetPoiDistances

    PREDICTION_TYPE_WEATHER_FORECAST = 0
    PREDICTION_TYPE_CUSTOM_STORM = 1

    WIND_DIRS = [0, 45, 90, 135, 180, 225, 270, 315]
    WIND_STRING_DICT = {0: 'N', 45: 'NO', 90: 'O', 135: 'ZO', 180: 'Z', 225: 'ZW', 270: 'W', 315: 'NW'}

    if 'temperature' not in st.session_state:
        st.session_state['wind_gusts'] = 90
    if 'wind_direction' not in st.session_state:
        st.session_state['wind_direction'] = 0
    if 'wind_speed' not in st.session_state:
        st.session_state['wind_speed'] = 40
    if 'wind_gusts' not in st.session_state:
        st.session_state['wind_speed'] = 40
    if 'precipitation' not in st.session_state:
        st.session_state['precipitation'] = 5

    if 'prediction_type' not in st.session_state:
        st.session_state['prediction_type'] = PREDICTION_TYPE_WEATHER_FORECAST
    if 'dates' not in st.session_state:
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        st.session_state['dates'] = (now, now + datetime.timedelta(hours=10))

    MODEL_NAMES = ['trees', 'buildings', 'roadsigns']
    for model_name in MODEL_NAMES:
        key = f'use_{model_name}'
        if key not in st.session_state:
            st.session_state[key] = True

    if 'use_pois' not in st.session_state:
            st.session_state['use_pois'] = False

    def set_model_fractions():
        model_fractions = {}
        # {model_name: int(st.session_state['model_use'][model_name]) for model_name in MODEL_NAMES}
        for model_name in MODEL_NAMES:
            model_fractions[model_name] = int(st.session_state[f'use_{model_name}'])

        if sum(list(model_fractions.values())) == 0:
            model_fractions = {model_name: 1 for model_name in MODEL_NAMES}

        st.session_state['model_fractions'] = model_fractions

        return model_fractions

    def on_change_model_select():
        set_model_fractions()
        agg_risks = aggregate_model_risks(st.session_state['risks'], MODEL_NAMES)
        st.session_state['risks']['service_areas'] = agg_risks['service_areas']
        st.session_state['risks']['zipcodes'] = agg_risks['zipcodes']
        st.session_state['risks']['grid'] = agg_risks['grid']
        return

    if 'model_fractions' not in st.session_state:
        set_model_fractions()

    st.title('Brandweer Amsterdam')
    if st.session_state['prediction_type'] == PREDICTION_TYPE_WEATHER_FORECAST:
        st.markdown(f'Voorspelling van **{st.session_state["dates"][0].strftime("%Y-%m-%d %H:%M")}** tot **{st.session_state["dates"][1].strftime("%Y-%m-%d %H:%M")}**')
    elif st.session_state['prediction_type'] == PREDICTION_TYPE_CUSTOM_STORM:
        st.markdown(f'**Eigen storm:**\
                    Temperatuur: **{st.session_state["temperature"]}**\
                    Wind Richting: **{WIND_STRING_DICT[st.session_state["wind_direction"]]}**\
                    Wind Snelheid: **{st.session_state["wind_speed"]}km/u**\
                    Wind Stoten: **{st.session_state["wind_gusts"]}km/u**\
                    Neerslag: **{st.session_state["precipitation"]}mm/u**'
                    )


    @st.cache_resource
    def load_tree_model():
        # model = Inference(model_name=pathlib.Path('xgboost_new_md20_sub50_tfr.pkl'),
        model = Inference(model_name=pathlib.Path('TEST_xgboost_model_trees.pkl'),
                                   model_dir=pathlib.Path('../src/models/trees/'),
                                   model_type='trees',
                                   grid_path=pathlib.Path('grid_trees_no_lines.csv'))

        return model


    @st.cache_resource
    def load_building_model():
        model = Inference(model_name=pathlib.Path('FINAL_xgboost_model_buildings.pkl'),
                                   model_dir=pathlib.Path('../src/models/buildings/'),
                                   model_type='buildings',
                                   grid_path=pathlib.Path('grid_buildings.csv'))

        return model


    @st.cache_resource
    def load_roadsign_model():
        # model = Inference(model_name=pathlib.Path('FINAL_xgboost_model_roadsigns.pkl'),
        model = Inference(model_name=pathlib.Path('xgboost_model_roadsigns.pkl'),
                                   model_dir=pathlib.Path('../src/models/roadsigns/'),
                                   model_type='roadsigns',
                                   grid_path=pathlib.Path('grid_roadsigns.csv'))

        return model


    @st.cache_data
    def load_component_data():
        service_areas: dict = json.load(open('service_areas.geojson'))

        zipcodes: dict = json.load(open('zipcodes_final.geojson'))

        grid: dict = json.load(open('grid_final.geojson'))

        firestations: dict = json.load(open('firestations.geojson'))

        map_bg = cv2.imread('map_bg_light.png', cv2.IMREAD_GRAYSCALE)
        _, buffer = cv2.imencode('.png', map_bg)
        base64_encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")

        return {'grid': grid,
                'zipcodes': zipcodes,
                'service_areas': service_areas,
                'icons': {'firestations': firestations},
                'map_bg': base64_encoded,}


    def _aggregate_grid_risks(grid_risks, scale, empty_areas_dict, grid):
        area_risks = empty_areas_dict.copy()

        zipped_risks = list(
                            # zip service_area per grid with risks per grid
                            zip(
                                # map grid['features'] to their service_area's
                                map(lambda feature: feature['properties'][scale],
                                    grid['features']),
                                # sort (key, val) on grid_id, then get the risks
                                [x[1] for x in sorted(list(grid_risks.items()), key=lambda x: int(x[0]))]))

        grouped_risks = groupby(sorted(zipped_risks, key=lambda x: x[0]), key=lambda x: x[0])

        for name, group in grouped_risks:
            values = [value for _, value in group]
            if values:
                area_risks[name] = list(np.mean(values, axis=0))

        return area_risks

    def get_risks(models, model_names, weather_params, api_dates, service_areas, zipcodes, grid):
        def _aggregate_model_risks(risk_dict):
            all_risks = []
            for model_name in model_names:
                all_risks.append(list(risk_dict[model_name]['grid'].values()))

            combined_grid_risks_list = np.average(all_risks, axis=0, weights=list(st.session_state['model_fractions'].values()))

            combined_grid_risks = {}
            for i, key in enumerate(risk_dict[model_name]['grid'].keys()):
                combined_grid_risks[key] = list(combined_grid_risks_list[i])

            return combined_grid_risks

        risk_dict = {}
        for model_name, model in zip(model_names, models):
            grid_risks = model.get_predictions(weather_params, api_dates)

            # remove some service_areas
            len_risks = len(list(grid_risks.values())[0])
            to_remove_service_areas = ['Aalsmeer', 'Uithoorn', 'Amstelveen']
                                    #    , 'Duivendrecht', 'Diemen', 'Driemond', 'Weesp']
            for feature in grid['features']:
                if feature['properties']['service_area'] in to_remove_service_areas:
                    grid_risks[int(feature['properties']['id'])] = [0] * len_risks

            zipcodes_risks = _aggregate_grid_risks(grid_risks, 'zipcode', {feature['properties']['pc4_code']: [] for feature in zipcodes['features']}, grid)
            service_areas_risks = _aggregate_grid_risks(grid_risks, 'service_area', {feature['properties']['name']: [] for feature in service_areas['features']}, grid)

            risk_dict[model_name] = dict({'service_areas': service_areas_risks, 'zipcodes': zipcodes_risks, 'grid': grid_risks})

        combined_grid_risks = _aggregate_model_risks(risk_dict)
        combined_zipcodes_risks = _aggregate_grid_risks(combined_grid_risks, 'zipcode', {feature['properties']['pc4_code']: [] for feature in zipcodes['features']}, grid)
        combined_service_areas_risks = _aggregate_grid_risks(combined_grid_risks, 'service_area', {feature['properties']['name']: [] for feature in service_areas['features']}, grid)

        risk_dict['grid'] = combined_grid_risks
        risk_dict['zipcodes'] = combined_zipcodes_risks
        risk_dict['service_areas'] = combined_service_areas_risks

        return risk_dict

    def aggregate_model_risks(risk_dict, model_names):
        all_grid_risks = []
        for model_name in model_names:
            model_grid_risk = risk_dict[model_name]['grid'].copy()
            if st.session_state['use_pois'] and 'poi_distances' in st.session_state:
                for grid_id in model_grid_risk:
                    model_grid_risk[grid_id] = [r * (1 + (10 * st.session_state['poi_distances'][grid_id])) for r in model_grid_risk[grid_id]]

            all_grid_risks.append(list(model_grid_risk.values()))

        combined_grid_risks_list = np.average(all_grid_risks, axis=0, weights=list(st.session_state['model_fractions'].values()))

        combined_grid_risks = {}
        for i, key in enumerate(risk_dict[model_names[0]]['grid'].keys()):
            combined_grid_risks[key] = list(combined_grid_risks_list[i])

        combined_zipcodes_risks = _aggregate_grid_risks(combined_grid_risks, 'zipcode', {feature['properties']['pc4_code']: [] for feature in component_data['zipcodes']['features']}, component_data['grid'])
        combined_service_areas_risks = _aggregate_grid_risks(combined_grid_risks, 'service_area', {feature['properties']['name']: [] for feature in component_data['service_areas']['features']}, component_data['grid'])

        return {'service_areas': combined_service_areas_risks, 'zipcodes': combined_zipcodes_risks, 'grid': combined_grid_risks}

    @st.cache_data
    def calc_risk_ranking(service_areas_risks, tree_risks, building_risks, roadsign_risks):
        mean_risks = []

        for items in zip(service_areas_risks, tree_risks, building_risks, roadsign_risks):
            service_area = items[0][0]
            risk_lists = [item[1] for item in items]
            mean_values = [sum(risk_values) / len(risk_values) if len(risk_values) > 0 else 0.0 for risk_values in risk_lists]
            mean_risks.append((service_area, *mean_values))


        risk_ranking = pd.DataFrame(mean_risks, columns=['service_area', 'risk', 'trees', 'buildings', 'roadsigns'])
        risk_ranking = risk_ranking.sort_values(by='risk', ascending=False)

        risk_ranking = risk_ranking.reset_index(drop=True)
        risk_ranking.index += 1

        risk_ranking = risk_ranking.rename(columns=
                                        {'service_area': 'Verzorgingsgebied',
                                            'risk': 'Risico',
                                            'trees': 'Bomen',
                                            'buildings': 'Gebouwen',
                                            'roadsigns': 'Overig'})

        risk_ranking_html = risk_ranking.to_html()
        risk_ranking_html = '<h1>Voorspelde risico per verzorgingsgebied</h1>' \
                        + f'<h3>gemaakt op: {str(datetime.date.today())}</h3>' \
                        + risk_ranking_html
                        # + f'<h3>methode: custom storm</h3>' \
                        # + f'<h3>storm data: ...</h3>' \
                        # + risk_ranking_html


        risk_ranking_pdf = pdf.from_string(risk_ranking_html)


        risk_ranking_csv = risk_ranking.to_csv()


        return risk_ranking, risk_ranking_html, risk_ranking_pdf, risk_ranking_csv

    tree_model = load_tree_model()
    building_model = load_building_model()
    roadsign_model = load_roadsign_model()
    component_data = load_component_data()

    if 'risks' not in st.session_state:
        st.session_state['risks'] = get_risks([tree_model, building_model, roadsign_model], MODEL_NAMES, {}, st.session_state['dates'], component_data['service_areas'], component_data['zipcodes'], component_data['grid'])

    component_data['risks'] = st.session_state['risks']


    col_comp, col_info, col_input = st.columns([13,13,4])
    map_return: dict = {}

    modal = my_modal.Modal('Nieuwe Storm', key='key', padding=10, max_width=1300)


    with col_comp:
        map_return = map_component(component_data['risks'],
                                component_data['grid'],
                                component_data['zipcodes'],
                                component_data['service_areas'],
                                component_data['icons'],
                                component_data['map_bg'])


    with col_info:
        if map_return['type'] == 'service_area':
            selected_area = map_return['name']
            if selected_area in component_data['risks']['service_areas']:
                risks = component_data['risks']['service_areas'][selected_area]
                tree_risks = component_data['risks']['trees']['service_areas'][selected_area]
                building_risks = component_data['risks']['buildings']['service_areas'][selected_area]
                roadsign_risks = component_data['risks']['roadsigns']['service_areas'][selected_area]
                mean_risk = sum(risks) / len(risks)
                mean_tree_risk = sum(tree_risks) / len(tree_risks)
                mean_building_risk = sum(building_risks) / len(building_risks)
                mean_roadsign_risk = sum(roadsign_risks) / len(roadsign_risks)

                st.markdown(f'''
                            **Verzorgingsgebied** **{selected_area}** (gemiddeld), **Risico**:{mean_risk:.2f}
                            <br> **Bomen**: {mean_tree_risk:.2f}
                            <br> **Gebouwen**: {mean_building_risk:.2f}
                            <br> **Overig**: {mean_roadsign_risk:.2f}
                            <br> **Gebruik** **POI**: {"ja" if st.session_state['use_pois'] else "nee"}
                            ''',
                            unsafe_allow_html=True)
        elif map_return['type'] == 'zipcode':
            selected_area = map_return['name']
            if selected_area in component_data['risks']['zipcodes']:
                risks = component_data['risks']['zipcodes'][selected_area]
                tree_risks = component_data['risks']['trees']['zipcodes'][selected_area]
                building_risks = component_data['risks']['buildings']['zipcodes'][selected_area]
                roadsign_risks = component_data['risks']['roadsigns']['zipcodes'][selected_area]
                mean_risk = sum(risks) / len(risks)
                mean_tree_risk = sum(tree_risks) / len(tree_risks)
                mean_building_risk = sum(building_risks) / len(building_risks)
                mean_roadsign_risk = sum(roadsign_risks) / len(roadsign_risks)

                st.markdown(f'''
                            **Postcode** **{selected_area}** (gemiddeld), **Risico**:{mean_risk:.2f}
                            <br> **Bomen**: {mean_tree_risk:.2f}
                            <br> **Gebouwen**: {mean_building_risk:.2f}
                            <br> **Overig**: {mean_roadsign_risk:.2f}
                            <br> **Gebruik** **POI**: {"ja" if st.session_state['use_pois'] else "nee"}
                            ''',
                            unsafe_allow_html=True)
        elif map_return['type'] == 'grid':
            selected_area = map_return['name']
            selected_grid = int(map_return['id'])

            if selected_grid in component_data['risks']['grid']:
                risks = component_data['risks']['grid'][selected_grid]
                tree_risks = component_data['risks']['trees']['grid'][selected_grid]
                building_risks = component_data['risks']['buildings']['grid'][selected_grid]
                roadsign_risks = component_data['risks']['roadsigns']['grid'][selected_grid]
                mean_risk = sum(risks) / len(risks)
                mean_tree_risk = sum(tree_risks) / len(tree_risks)
                mean_building_risk = sum(building_risks) / len(building_risks)
                mean_roadsign_risk = sum(roadsign_risks) / len(roadsign_risks)

                st.markdown(f'''
                                **Grid** **{selected_area}**|**{selected_grid}** (gemiddeld), **Risico**:{mean_risk:.2f}
                                <br> **Bomen**: {mean_tree_risk:.2f}
                                <br> **Gebouwen**: {mean_building_risk:.2f}
                                <br> **Overig**: {mean_roadsign_risk:.2f}
                                <br> **Gebruik** **POI**: {"ja" if st.session_state['use_pois'] else "nee"}
                                ''',
                                unsafe_allow_html=True)
        else:
            st.markdown(f'''
                            Selecteer verzorgingsgebied voor informatie.
                            <br> **Bomen**:
                            <br> **Gebouwen**:
                            <br> **Overig**:
                            <br> **Gebruik** **POI**: {"ja" if st.session_state['use_pois'] else "nee"}
                            ''',
                            unsafe_allow_html=True)


        risk_ranking, risk_ranking_html, risk_ranking_pdf, risk_ranking_csv = \
            calc_risk_ranking(list(component_data['risks']['service_areas'].items()),
                              list(component_data['risks']['trees']['service_areas'].items()),
                              list(component_data['risks']['buildings']['service_areas'].items()),
                              list(component_data['risks']['roadsigns']['service_areas'].items()))


        tab_text, tab_tree, tab_building, tab_roadsign = st.tabs(['Risico Ranking', 'Bomen', 'Gebouwen', 'Overig'])
        with tab_text:
            st.markdown('**Verzorgingsgebied** **risico** **ranking**:')
            st.dataframe(risk_ranking, height=270)

            col_pdf, col_csv = st.columns([1,3])
            with col_pdf:
                st.download_button(
                    label='Download pdf',
                    data=risk_ranking_pdf,
                    file_name=f'risks_{str(datetime.date.today())}.pdf',
                    mime='application/pdf'
                )
            with col_csv:
                st.download_button(
                    label='Download csv',
                    data=risk_ranking_csv,
                    file_name=f'risks_{str(datetime.date.today())}.csv',
                    mime='text/csv'
                )


    with col_input:
        open_modal = st.button('Nieuwe Storm', type='primary')
        if open_modal:
            modal.open()

        st.checkbox('Bomen', on_change=on_change_model_select, key='use_trees')
        st.checkbox('Gebouwen', on_change=on_change_model_select, key='use_buildings')
        st.checkbox('Overig', on_change=on_change_model_select, key='use_roadsigns')
        st.checkbox('POI\'s', on_change=on_change_model_select, key='use_pois')

        if modal.is_open():
            with modal.container():
                    weather_params = {}
                    tab_new, tab_old, tab_forecast, tab_csv = st.tabs(['Maak Nieuwe Storm', 'Kies Oude Storm', 'Weer Voorspelling', 'Upload CSV'])
                    with tab_new:
                        with st.form('storm_input_form'):
                            col_temp, _, col_wind_direction, _, col_wind_speed, _, col_wind_gusts = st.columns([10, 1, 10, 1, 10, 1, 10])
                            temperature = 10
                            if 'temperature' in st.session_state:
                                temperature = st.session_state['temperature']

                            st.session_state['temperature'] =  col_temp.select_slider('Temperatuur', options=list(range(-20, 41, 5)), value=temperature)

                            wind_dir_index = 0
                            if 'wind_direction' in st.session_state:
                                wind_dir_index = WIND_DIRS.index(st.session_state['wind_direction'])

                            st.session_state['wind_direction'] = col_wind_direction.selectbox('Kies Wind Richting',
                                                                        WIND_DIRS,
                                                                        index=wind_dir_index,
                                                                        format_func=lambda w: WIND_STRING_DICT[w])


                            wind_speed = 40
                            if 'wind_speed' in st.session_state:
                                wind_speed = st.session_state['wind_speed']

                            st.session_state['wind_speed'] = col_wind_speed.select_slider('Wind Snelheid (km/u)', options=list(range(0, 161, 10)), value=wind_speed)

                            wind_gusts = 40
                            if 'wind_gusts' in st.session_state:
                                wind_gusts = st.session_state['wind_gusts']

                            st.session_state['wind_gusts'] = col_wind_speed.select_slider('Wind Stoten (km/u)', options=list(range(0, 161, 10)), value=wind_gusts)


                            # precipitation_classes = ['Licht', 'Gemiddeld', 'Zwaar', 'Extreem']
                            precipitation_classes = [5, 10, 25, 50]
                            precipitation_string_dict = {5: 'Licht', 10: 'Gemiddeld', 25: 'Zwaar', 50: 'Extreem'}
                            precipitation_index = 0

                            if 'precipitation' in st.session_state:
                                precipitation_index = precipitation_classes.index(st.session_state['precipitation'])

                            st.session_state['precipitation'] = col_wind_gusts.radio('Neerslag (mm/u)',
                                                                                    precipitation_classes,
                                                                                    index=precipitation_index,
                                                                                    format_func=lambda p:f'{precipitation_string_dict[p]} ({p}mm)')

                            _, col_submit = st.columns([14,1])
                            with col_submit:
                                if st.form_submit_button('Submit', type='primary'):
                                    weather_params = {'temperature_2m': [st.session_state['temperature']],
                                                    'precipitation': [st.session_state['precipitation']],
                                                    'wind_speed_10m': [st.session_state['wind_speed']],
                                                    'wind_gusts_10m': [st.session_state['wind_gusts']],
                                                    'wind_direction_10m': [st.session_state['wind_direction']]
                                                    }

                                    st.session_state['risks'] = get_risks([tree_model, building_model, roadsign_model], MODEL_NAMES, weather_params, (), component_data['service_areas'], component_data['zipcodes'], component_data['grid'])
                                    st.session_state['prediction_type'] = PREDICTION_TYPE_CUSTOM_STORM
                                    modal.close()

                    with tab_old:
                        tab_old.text('Choose Storm')
                        tab_old.radio('Previous Storms', ['Agner', 'Babet', 'Debi', 'Piet'])
                        # form submit weather_params = read_csv(storm)

                    with tab_forecast:
                        st.text('Weer Voorspelling')
                        col_days, col_time, col_date = st.columns([1,1,3])
                        with st.form('storm_forecast_form'):

                            with col_days:
                                today = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
                                tomorrow = today + datetime.timedelta(days=1)
                                overmorrow = today + datetime.timedelta(days=2)
                                twovermorrow = today + datetime.timedelta(days=3)
                                st.text('Aankomende Dagen')
                                st.markdown('<div style="height: 1vh; background-color: transparent;"></div>', unsafe_allow_html=True)
                                if st.button('Vandaag', use_container_width=True):
                                    st.session_state['dates'] = (today, tomorrow)
                                if st.button('Morgen', use_container_width=True):
                                    st.session_state['dates'] = (tomorrow, overmorrow)
                                if st.button('Overmorgen', use_container_width=True):
                                    st.session_state['dates'] = (overmorrow, twovermorrow)

                            with col_time:
                                st.text('Tijden')
                                input_time0 = st.time_input('Tijd Dag 1', st.session_state['dates'][0], step = datetime.timedelta(hours=1))
                                input_time1 = st.time_input('Tijd Dag 2', st.session_state['dates'][1], step = datetime.timedelta(hours=1))

                            with col_date:
                                st.text('Kies Dagen met Calender')
                                today = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
                                dates = (today, today + datetime.timedelta(days=1))
                                if 'dates' in st.session_state:
                                    dates = st.session_state['dates']

                                input_dates = st.date_input(
                                    'Kies periode om te voorspellen',
                                    dates,
                                    format='YYYY.MM.DD',
                                )

                            _, col_submit = st.columns([14,1])
                            with col_submit:
                                if st.form_submit_button('Submit', type='primary'):
                                    st.session_state['dates'] = (datetime.datetime.combine(input_dates[0], input_time0), datetime.datetime.combine(input_dates[1], input_time1))
                                    st.session_state['risks'] = get_risks([tree_model, building_model, roadsign_model], MODEL_NAMES, {}, st.session_state['dates'], component_data['service_areas'], component_data['zipcodes'], component_data['grid'])
                                    st.session_state['prediction_type'] = PREDICTION_TYPE_WEATHER_FORECAST
                                    modal.close()


                    with tab_csv:
                        st.text('Upload CSV')
                        storm_data = st.file_uploader('Storm Data')
                        # form submit weather_params = storm_data

    with tab_tree:
        plt.clf()
        fig, ax = tree_model.get_explainer_plot()
        st.pyplot(fig)

    with tab_building:
        plt.clf()
        fig, ax = building_model.get_explainer_plot()
        st.pyplot(fig)

    with tab_roadsign:
        plt.clf()
        fig, ax = roadsign_model.get_explainer_plot()
        st.pyplot(fig)


    @st.cache_resource
    def make_poi_getter():
        POI_distances = GetPoiDistances(grid_path='grid_by_hand.csv')
        POI_distances.get_distances()

        return POI_distances

    if 'get_poi_distances' not in st.session_state:
        st.session_state['get_poi_distances'] = make_poi_getter()
        distances_df = st.session_state['get_poi_distances'].grid_gdf

        st.session_state['poi_distances'] = {id: distance for (id, distance) in list(zip(distances_df['id'], distances_df['summed_distance']))}
