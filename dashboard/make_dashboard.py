def make_dashboard():
    import streamlit as st
    import streamlit_modal as stmodal
    import my_modal
    import pandas as pd
    import json
    import cv2
    import base64
    from itertools import groupby
    import pdfkit as pdf
    import datetime

    from component import map_component

    if 'temperature' not in st.session_state:
        st.session_state['wind_gusts'] = 10
    if 'wind_direction' not in st.session_state:
        st.session_state['wind_direction'] = 'N'
    if 'wind_speed' not in st.session_state:
        st.session_state['wind_speed'] = 40
    if 'wind_gusts' not in st.session_state:
        st.session_state['wind_speed'] = 40
    if 'percipitation' not in st.session_state:
        st.session_state['percipitation'] = 'Licht'

    st.title('Storm: ...')

    @st.cache_data
    def load_component_data():
        service_areas: dict = json.load(open('service_areas.geojson'))

        grid: dict = json.load(open('grid_by_hand.geojson'))

        firestations: dict = json.load(open('firestations.geojson'))

        map_bg = cv2.imread('map_bg_big.png', cv2.IMREAD_GRAYSCALE)
        _, buffer = cv2.imencode('.png', map_bg)
        base64_encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")

        grid_risks: dict = json.load(open('grid_by_hand_risks.json'))

        service_areas_risks = {feature['properties']['name']: [] for feature in service_areas['features']}

        zipped_risks = list(zip(map(lambda feature: feature['properties']['service_area'], grid['features']),
                                [x[1] for x in sorted(list(grid_risks.items()), key=lambda x: int(x[0]))]))
        grouped_risks = groupby(sorted(zipped_risks, key=lambda x: x[0]), key=lambda x: x[0])

        for name, group in grouped_risks:
            values = [value for _, value in group]
            if values:
                service_areas_risks[name] = sum(values) / len(values)

        return {'risks': {'service_areas': service_areas_risks, 'grid': grid_risks},
            'grid': grid,
            'service_areas': service_areas,
            'icons': {'firestations': firestations},
            'map_bg': base64_encoded,}

    component_data = load_component_data()

    col0, _, col1, _, col2 = st.columns([17,1,17,1,3])
    map_return: dict = {}

    with col2:
        modal = my_modal.Modal('Nieuwe Storm', key='key', padding=10, max_width=1300)
        open_modal = st.button('Nieuwe Storm', type='primary')
        if open_modal:
            modal.open()

        if modal.is_open():
            with modal.container():
                tab0, tab1, tab2, tab3 = st.tabs(['Maak Nieuwe Storm', 'Kies Oude Storm', 'Weer Voorspelling', 'Upload CSV'])
                with tab0:
                    ccol1, _, ccol2, _, ccol3, _, ccol4 = st.columns([10, 1, 10, 1, 10, 1, 10])
                    temperature = 10
                    if 'temperature' in st.session_state:
                        temperature = st.session_state['temperature']

                    st.session_state['temperature'] = ccol1.select_slider('Temperatuur', options=list(range(-20, 41, 5)), value=temperature)

                    wind_dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                    wind_dir_index = 0
                    if 'wind_direction' in st.session_state:
                        wind_dir_index = wind_dirs.index(st.session_state['wind_direction'])

                    st.session_state['wind_direction'] = ccol2.selectbox('Kies Wind Richting',
                                                                ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                                                                index=wind_dir_index)


                    wind_speed = 40
                    if 'wind_speed' in st.session_state:
                        wind_speed = st.session_state['wind_speed']

                    st.session_state['wind_speed'] = ccol3.select_slider('Wind Snelheid', options=list(range(0, 161, 10)), value=wind_speed)

                    wind_gusts = 40
                    if 'wind_gusts' in st.session_state:
                        wind_gusts = st.session_state['wind_gusts']

                    st.session_state['wind_gusts'] = ccol3.select_slider('Wind Stoten', options=list(range(0, 161, 10)), value=wind_gusts)


                    percipitation_classes = ['Licht', 'Gemiddeld', 'Zwaar', 'Extreem']
                    percipitation_index = 0

                    if 'percipitation' in st.session_state:
                        percipitation_index = percipitation_classes.index(st.session_state['percipitation'])

                    st.session_state['percipitation'] = ccol4.radio('Neerslag', percipitation_classes, index=percipitation_index)

            with tab1:
                tab1.text('Choose Storm')
                tab1.radio('Previous Storms', ['Agner', 'Babet', 'Debi', 'Piet'])

            with tab2:
                st.text('From Weather Forecast')
                st.radio('Day', ['Today', 'Tomorrow', 'Overmorrow'])

            with tab3:
                st.text('Upload CSV')
                st.file_uploader('Storm Data')



    with col0:
        map_return = map_component(component_data['risks'],
                                component_data['grid'],
                                component_data['service_areas'],
                                component_data['icons'],
                                component_data['map_bg'])


    with col1:
        if map_return['type'] == 'service_area':
            selected_area = map_return['name']
            if selected_area in component_data['risks']['service_areas']:
                st.text(f'{selected_area}, Risico:{component_data["risks"]["service_areas"][selected_area]:.2f}\nInfo\nInfo')
        elif map_return['type'] == 'grid':
            selected_area = map_return['id']
            if selected_area in component_data['risks']['grid']:
                st.text(f'{map_return["name"]}:{selected_area}\nGrid Risico:{component_data["risks"]["grid"][selected_area]:.2f}\nInfo\nInfo\nInfo')


        risk_ranking = pd.DataFrame(list(component_data['risks']['service_areas'].items()), columns=['service_area', 'risk'])
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

        st.dataframe(risk_ranking, height=340)

        risk_ranking_html = risk_ranking.to_html()
        risk_ranking_html = '<h1>Voorspelde risico per verzorgingsgebied</h1>' \
                        + f'<h3>gemaakt op: {str(datetime.date.today())}</h3>' \
                        + f'<h3>methode: custom storm</h3>' \
                        + f'<h3>storm data: ...</h3>' \
                        + risk_ranking_html


        risk_ranking_pdf = pdf.from_string(risk_ranking_html)


        risk_ranking_csv = risk_ranking.to_csv()

        ccol0, ccol1 = st.columns([1,4])
        with ccol0:
            st.download_button(
                label='Download pdf',
                data=risk_ranking_pdf,
                file_name=f'risks_{str(datetime.date.today())}.pdf',
                mime='application/pdf'
            )
        with ccol1:
            st.download_button(
                label='Download csv',
                data=risk_ranking_csv,
                file_name=f'risks_{str(datetime.date.today())}.csv',
                mime='text/csv'
            )

