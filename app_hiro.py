import streamlit as st
from streamlit_folium import st_folium, folium_static
import folium
from folium.plugins import FastMarkerCluster, MarkerCluster, HeatMap
import json
import pandas as pd
import geopandas as gpd
import plotly.express as px
from shapely.geometry import Polygon, Point
import os
import sys
import numpy as np

sys.path.append("./src/")
import budget_calculation as budget_lib

st.set_page_config(layout="wide")

# Functions
def color_function_stufen(feature):
    category = feature['properties']['stufe']
    if category == 1:
        color = '#b7f598' # green
    elif category == 2:
        color = '#f5d998' # orange
    elif category == 3:
        color = '#f59c98'  # red
    
    return {
        'fillColor': color,
        'color': color,
        'weight': 1,
        'fillOpacity': 1
    }


## Load Data
DATA_PATH = "./data"
lst_path = os.path.join(DATA_PATH, "interim/landsat",
                        "LC09_L1TP_192024_20220719_20230406_02_T1",
                        "LC09_L1TP_192024_20220719_20230406_02_T1_LST_Dresden.npy")
st.session_state.lst = np.load(lst_path)

stufen_path = os.path.join(DATA_PATH, "interim/stufen.json")
st.session_state.stufen = gpd.read_file(stufen_path)
combined_geom = st.session_state.stufen.dissolve().to_crs("epsg:4326")
centroid = combined_geom.geometry.centroid
centroid_point = centroid.iloc[0]
longitude = centroid.x.values[0]
latitude = centroid.y.values[0]

objekte_path = os.path.join(DATA_PATH, "interim/objekte.json")
st.session_state.objekte = gpd.read_file(objekte_path)

bb_path = os.path.join(DATA_PATH, "interim/buergerbeteiligung_dresden.json")
st.session_state.bb = gpd.read_file(bb_path)

population_path = os.path.join(DATA_PATH, "interim/population_dresden.json")
st.session_state.population = gpd.read_file(population_path)

massnahmen_path = os.path.join(DATA_PATH, "raw/Maßnahmenkatalog.csv")
st.session_state.massnahmen = pd.read_csv(massnahmen_path, sep=';')

### APP

## Title
st.title("HiRo :sun_with_face:")
st.markdown("Cool down - Hack die Extreme | 24.\-26. Mai 2024 | HTW Dresden")
##### Risk Navigator

col1, col2 = st.columns([1, 2])
with col1:  
    # Objects
    st.header("Belastete Gebiete")
    st.multiselect(label="Wähle ein Objekt Art", options=["Bushaltestelle", "Kita", "Ambulantepflege"], default=["Bushaltestelle"], key="object_selection")
    
    # Risk
    st.header("Gefahrenstufen")
    st.multiselect(label="Gefahrenstufen", options=["Stufe 1", "Stufe 2", "Stufe 3"], default=["Stufe 1", "Stufe 2", "Stufe 3"], key="risk")
    selected_risk = [int(s.split(" ")[1]) for s in st.session_state.risk]
    sub_selection = st.session_state.objekte.loc[(st.session_state.objekte["stufe"].isin(selected_risk)) & \
                                                 (st.session_state.objekte["objekt"].isin(st.session_state.object_selection)), :]
    
    # Bar Chart
    objekt_summary = sub_selection.loc[:, ["stufe", "groesste_v_gruppe"]].value_counts().reset_index()
    fig = px.bar(objekt_summary,  x="stufe", y="count", color="groesste_v_gruppe", text_auto=True, height=300)
    fig.update_yaxes(title="Anzahl Objekte", range=(0, 1.2 * len(sub_selection["stufe"]==2)))
    fig.update_xaxes(title="Hitzebelastungsstufe")
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0), title="Objekte nach belastung und größte (vulnerable) Altersgruppe")
    st.plotly_chart(fig, use_container_width=True)


with col2:
    st.header(f"Analysierte Objekte: {len(sub_selection)}")
    m = folium.Map(location=[latitude, longitude], zoom_start=11, tiles="cartodb positron")

    bus_stop_coords = list(sub_selection.loc[:, ["lat", "lon"]].values)
    #HeatMap(bus_stop_coords, opacity=1).add_to(m)
    folium.GeoJson(st.session_state.stufen, style_function=color_function_stufen, opacity=0.3, interactive=True,name="Belastungsstufen").add_to(m)
    #folium.LayerControl(collapsed=False).add_to(m)

    marker_cluster = MarkerCluster(bus_stop_coords[:1], 
                                   options={
                                    'spiderfyOnMaxZoom': False,
                                    'showCoverageOnHover': True,
                                    'zoomToBoundsOnClick': True,
                                    'disableClusteringAtZoom': 14,  # Disable clustering at zoom level 16 and above
                                    'maxClusterRadius': 50  # The maximum radius that a cluster will cover from the central marker (in pixels)
                                },
                                opacity=1
                                ).add_to(m)
    
    category_icons = {
        'Bushaltestelle': "bus",
        'Kita': "baby",
        'Ambulantepflege':"person-cane"}
    

    for row in sub_selection.itertuples():
        icon = folium.Icon(color="green",icon=category_icons[getattr(row, "objekt")], prefix='fa')
        folium.Marker(location=[row.lat, row.lon], icon=icon, popup=row.name).add_to(marker_cluster)
    
    # Add Comments
    color_dict = {
            "Etwas cool": "blue",
            "Neutral":"green",
            "Etwas warm": "yellow",
            "Warm": "orange",
            "Sehr warm": "red"}

    st.checkbox(label="Kommentare zeigen", key="comments_bool")
    if st.session_state.comments_bool:
        for row in st.session_state.bb.itertuples():
            html = '''
                <b>Datum: </b>{datum} <br>
                <b>Komfort: </b>{komfort} <br>
                <b>Vorschlag: </b>{vorschlag}
                '''.format(datum=row.CreationDate, komfort=row.Komfort, vorschlag=row.Vorschlag)

            icon = folium.Icon(color=color_dict[getattr(row, "Komfort")], icon="comment", prefix='fa')
            folium.Marker(location=[row.lat, row.lon], 
                icon=icon, 
                popup = folium.Popup(html, parse_html=False, max_width=200),
                ).add_to(m)

    folium_static(m)

st.header("Maßnahmenpriorisierung")

col1, col2 = st.columns([1, 2])

with col1:
    st.slider(label='Budget (€)', min_value=10000, max_value=2000000, step=10000, key="budget")
    budget_df = budget_lib.calculate_actions_in_budget(st.session_state.budget, measures_gdf=sub_selection, data_path=DATA_PATH)
    budget_df["lat"] = budget_df["geometry"].apply(lambda point: point.y)
    budget_df["lon"] = budget_df["geometry"].apply(lambda point: point.x)
    budget_df = budget_df.loc[budget_df["action"].notna(),["stufe", "stufe_post_action", "action", "cost", "lat", "lon", "geometry"]]
    summary = budget_df.loc[:, ["stufe", "stufe_post_action", "action", "cost"]].groupby(["stufe", "stufe_post_action", "action"]).agg(["sum", "count"])
    summary = summary.rename(columns={"sum":"Gesamtkosten", "count":"Anzahl"})
    summary.columns = summary.columns.droplevel(0)
    st.dataframe(summary)

    # Spider
    data = st.session_state.massnahmen
    #st.dataframe(data)
    # Filtere die Daten für den ausgewählten Namen
    # Dropdown-Menü für Namen
    selected_name = st.selectbox('Wählen Sie einen Maßnahmen:', data['Name'].unique())
    # Filtere die Daten für den ausgewählten Namen
    filtered_data = data[data['Name'] == selected_name]
    
    # Radar-Chart erstellen
    fig = px.line_polar(data, r=[0.75, 0.8, 0.6],
                        theta=['rel Invest (€)', 'rel Impact area (m²)', 'rel Avg. Heat Reduction Efficiency (°C)'],
                        line_close=True, title='Dynamischer Radar-Chart')

    fig.update_traces(fill='toself')
    st.plotly_chart(fig)

with col2:
    st.header(f"Vorschlagen: {len(budget_df)}")
    m2 = folium.Map(location=[latitude, longitude], zoom_start=11, tiles="cartodb positron")

    budget_marker_coords = list(budget_df.loc[:, ["lat", "lon"]].values)

    category_icons = {
        'tree': "tree-city",
        'green_pergola': "torii-gate",
        'thermal_foil':"arrow-up-right-from-square"}


    for row in budget_df.itertuples():
        intervention_colors = {0:"grey", 1:"green", 2:'yellow'} 

        html = '''
                <b>Maßnahme: </b>{action} <br>
                <b>Ist-Stufe: </b>{stufe} <br>
                <b>Soll-Stufe: </b>{stufe2} <br>
                '''.format(action=row.action, stufe=row.stufe, stufe2=row.stufe_post_action)
        
        color=intervention_colors[getattr(row, "stufe_post_action")]
        icon = folium.Icon(icon=category_icons[getattr(row, "action")], prefix='fa', color="green") 
        
        folium.Marker(location=[row.lat, row.lon], icon=icon,
            popup = folium.Popup(html, parse_html=False, max_width=200)).add_to(m2)
    
    folium_static(m2)