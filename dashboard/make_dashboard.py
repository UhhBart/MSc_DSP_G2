def make_dashboard():
    import sys
    sys.path.append('../src')

    import streamlit as st
    import my_modal
    import pandas as pd
    import json
    import cv2
    import base64
    from itertools import groupby
    import pdfkit as pdf
    import datetime
    import pathlib
    import datetime

    from component import map_component
    from TreeInference import makeTreePrediction

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

    if 'dates' not in st.session_state:
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        st.session_state['dates'] = (now, now + datetime.timedelta(hours=10))

    st.title('Brandweer Amsterdam')
    st.markdown(f'Voorspelling van **{st.session_state["dates"][0].strftime("%Y-%m-%d %H:%M")}** tot **{st.session_state["dates"][1].strftime("%Y-%m-%d %H:%M")}**')


    @st.cache_resource
    def load_tree_model():
        model = makeTreePrediction(model_name=pathlib.Path('xgboost_md15_sub90.pkl'),
                                   model_dir=pathlib.Path('../src/models/trees/'),
                                   grid_path=pathlib.Path('grid_by_hand_enriched.csv'))

        return model


    @st.cache_data
    def load_component_data():
        service_areas: dict = json.load(open('service_areas.geojson'))

        grid: dict = json.load(open('grid_by_hand.geojson'))

        firestations: dict = json.load(open('firestations.geojson'))

        map_bg = cv2.imread('map_bg_light.png', cv2.IMREAD_GRAYSCALE)
        _, buffer = cv2.imencode('.png', map_bg)
        base64_encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")

        return {'grid': grid,
                'service_areas': service_areas,
                'icons': {'firestations': firestations},
                'map_bg': base64_encoded,}


    def get_risks(tree_model, weather_params, api_dates, service_areas, grid):
        print('in get_risks')
        grid_risks = tree_model.get_predictions(weather_params, api_dates)
        grid_risks = {key: grid_risks[key] for key in grid_risks}
        # print(grid_risks)
        # exit()
        service_areas_risks = {feature['properties']['name']: [] for feature in service_areas['features']}

        zipped_risks = list(
                            # zip service_area per grid with risks per grid
                            zip(
                                # map grid['features'] to their service_area's
                                map(lambda feature: feature['properties']['service_area'],
                                    grid['features']),
                                # sort (key, val) on grid_id, then get the risks
                                [x[1] for x in sorted(list(grid_risks.items()), key=lambda x: int(x[0]))]))

        grouped_risks = groupby(sorted(zipped_risks, key=lambda x: x[0]), key=lambda x: x[0])

        for name, group in grouped_risks:
            values = [value for _, value in group]
            if values:
                service_areas_risks[name] = [sum(column) / len(column) for column in zip(*values)]


        return {'service_areas': service_areas_risks, 'grid': grid_risks}

    @st.cache_data
    def calc_risk_ranking(service_areas_risks):
        mean_risks = []

        for item in service_areas_risks:
            service_area = item[0]
            risk_values = item[1]
            mean_value = sum(risk_values) / len(risk_values) if len(risk_values) > 0 else 0.0
            mean_risks.append((service_area, mean_value))



        risk_ranking = pd.DataFrame(mean_risks, columns=['service_area', 'risk'])
        risk_ranking = risk_ranking.sort_values(by='risk', ascending=False)

        risk_ranking = risk_ranking.reset_index(drop=True)
        risk_ranking.index += 1

        risk_ranking['trees'] = risk_ranking['risk'] + 0.0444
        risk_ranking['buildings'] = risk_ranking['risk'] - 0.0333
        risk_ranking['rest'] = risk_ranking['risk'] - 0.0111

        risk_ranking = risk_ranking.rename(columns=
                                        {'service_area': 'Verzorgingsgebied',
                                            'risk': 'Risico',
                                            'trees': 'Bomen',
                                            'buildings': 'Gebouwen',
                                            'rest': 'Overig'})

        risk_ranking_html = risk_ranking.to_html()
        risk_ranking_html = '<h1>Voorspelde risico per verzorgingsgebied</h1>' \
                        + f'<h3>gemaakt op: {str(datetime.date.today())}</h3>' \
                        + f'<h3>methode: custom storm</h3>' \
                        + f'<h3>storm data: ...</h3>' \
                        + risk_ranking_html


        risk_ranking_pdf = pdf.from_string(risk_ranking_html)


        risk_ranking_csv = risk_ranking.to_csv()


        return risk_ranking, risk_ranking_html, risk_ranking_pdf, risk_ranking_csv

    tree_model = load_tree_model()
    component_data = load_component_data()

    if 'risks' not in st.session_state:
        st.session_state['risks'] = get_risks(tree_model, {}, st.session_state['dates'], component_data['service_areas'], component_data['grid'])

    component_data['risks'] = st.session_state['risks']


    col_comp, col_info, col_input = st.columns([13,13,4])
    map_return: dict = {}

    modal = my_modal.Modal('Nieuwe Storm', key='key', padding=10, max_width=1300)


    with col_comp:
        map_return = map_component(component_data['risks'],
                                component_data['grid'],
                                component_data['service_areas'],
                                component_data['icons'],
                                component_data['map_bg'])


    with col_info:
        if map_return['type'] == 'service_area':
            selected_area = map_return['name']
            if selected_area in component_data['risks']['service_areas']:
                risks = component_data["risks"]["service_areas"][selected_area]
                mean_risk = sum(risks) / len(risks)
                st.markdown(f'''
                            **Verzorgingsgebied** **{selected_area}** (gemiddeld), **Risico**:{mean_risk:.2f}
                            <br> **Bomen**: {mean_risk:.2f}
                            <br> **Gebouwen**: {mean_risk:.2f}
                            <br> **Overig**: {mean_risk:.2f}
                            ''',
                            unsafe_allow_html=True)
        elif map_return['type'] == 'grid':
            selected_area = map_return['name']
            selected_grid = int(map_return['id'])

            if selected_grid in component_data['risks']['grid']:
                risks = component_data["risks"]["grid"][selected_grid]
                mean_risk = sum(risks) / len(risks)
                st.markdown(f'''
                                **Grid** **{selected_area}**|**{selected_grid}** (gemiddeld), **Risico**:{mean_risk:.2f}
                                <br> **Bomen**: {mean_risk:.2f}
                                <br> **Gebouwen**: {mean_risk:.2f}
                                <br> **Overig**: {mean_risk:.2f}
                                ''',
                                unsafe_allow_html=True)
        else:
            st.markdown(f'''
                            Selecteer verzorgingsgebied voor informatie.
                            <br> **Bomen**:
                            <br> **Gebouwen**:
                            <br> **Overig**:
                            ''',
                            unsafe_allow_html=True)


        risk_ranking, risk_ranking_html, risk_ranking_pdf, risk_ranking_csv = \
            calc_risk_ranking(list(component_data['risks']['service_areas'].items()))


        tab_text, tab_plot = st.tabs(['Risico Ranking', 'Analyse'])
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

                            # wind_dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                            wind_dirs = [0, 45, 90, 135, 180, 225, 270, 315]
                            wind_string_dict = {0: 'N', 45: 'NO', 90: 'O', 135: 'ZO', 180: 'Z', 225: 'ZW', 270: 'W', 315: 'NW'}
                            wind_dir_index = 0
                            if 'wind_direction' in st.session_state:
                                wind_dir_index = wind_dirs.index(st.session_state['wind_direction'])

                            st.session_state['wind_direction'] = col_wind_direction.selectbox('Kies Wind Richting',
                                                                        wind_dirs,
                                                                        index=wind_dir_index,
                                                                        format_func=lambda w: wind_string_dict[w])


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

                                    st.session_state['risks'] = get_risks(tree_model, weather_params, (), component_data['service_areas'], component_data['grid'])
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
                                    st.session_state['risks'] = get_risks(tree_model, {}, st.session_state['dates'], component_data['service_areas'], component_data['grid'])
                                    modal.close()


                    with tab_csv:
                        st.text('Upload CSV')
                        storm_data = st.file_uploader('Storm Data')
                        # form submit weather_params = storm_data
