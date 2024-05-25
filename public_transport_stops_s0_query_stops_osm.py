import sys

sys.path.append(".")

import requests
import json
import os
import pandas as pd
import geopandas as gpd
from pyproj import Proj, transform

import utils
import constants as const


city_name = const.CITY
query_bus_stops = f"""[out:json][timeout:100];
area[name="{city_name}"]->.searchArea;
(
nwr(area.searchArea)["highway"="bus_stop"];
nwr(area.searchArea)["railway"="tram_stop"];
);
out;"""

filename = "bus_stops_dresden_osm_raw.json"
if not os.path.exists(const.SAVE_DIRECTORY):
    os.makedirs(const.SAVE_DIRECTORY)
bus_stops_path = os.path.join(const.SAVE_DIRECTORY, filename)

if not os.path.exists(bus_stops_path):
    data = utils.run_overpass_query(query_bus_stops)
    with open(bus_stops_path, "w") as file:
        json.dump(json.loads(data), file)
