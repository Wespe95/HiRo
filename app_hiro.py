import streamlit as st
from streamlit_folium import st_folium, folium_static
import pandas as pd
import geopandas as gpd
import plotly.express as px
import os
import sys
sys.path.append("./src/heat_waves")
import data_tools as data_tools
import plots as plot_lib
import numpy as np


st.set_page_config(layout="wide")

# Data
DATA_PATH = "./data"
lst_path = os.path.join(DATA_PATH, "interim/landsat",
                        "LC09_L1TP_192024_20220719_20230406_02_T1",
                        "LC09_L1TP_192024_20220719_20230406_02_T1_LST_Dresden.npy")
st.session_state.lst = np.load(lst_path)
st.session_state.stufen = pd.read_csv(os.path.join(DATA_PATH, "interim/stufen.csv"))
st.session_state.stufen = gpd.GeoDataFrame(st.session_state.stufen, geometry="geometry")

## Title
st.title("HiRo")

##### Country Scale
st.header("Hitze Risikoindex")

col1, col2 = st.columns([2,1])
with col2:
    st.slider(label="Oberflächentemperatur", min_value=0, max_value=40, value=(27, 40), key="risk_index")
    st.markdown(st.session_state.risk_index)
    st.multiselect(label="Risikogruppen", options=["bus stops", "kitas", "Pflegeheime", ])
with col1: 
    masked_lst = np.ma.masked_outside(st.session_state.lst, st.session_state.risk_index[0], st.session_state.risk_index[1])
    lst_with_nan = masked_lst.filled(np.nan)
    st.plotly_chart(px.imshow(lst_with_nan, color_continuous_scale="sunsetdark", width=1000), 
                    use_container_width=True)


st.header("Vulnerabilität")

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
    
combined_geom = st.session_state.stufen.dissolve().to_crs("epsg:4326")
centroid = combined_geom.geometry.centroid
centroid_point = centroid.iloc[0]
longitude = centroid.x.values[0]
latitude = centroid.y.values[0]

m = st_folium.Map(location=[latitude, longitude], zoom_start=11, tiles="cartodb positron")

# Add the polygons to the map
st_folium.GeoJson(st.session_state.stufen, style_function=color_function_stufen, interactive=True,name="Belastungsstufen").add_to(m)
st_folium.LayerControl(collapsed=False).add_to(m)
m