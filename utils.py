import requests
import json
import os
import pandas as pd
import geopandas as gpd
from pyproj import Proj, transform, Transformer

import constants as const


# query stops from OSM
def run_overpass_query(ql_query):
    """Run an overpass query"""

    overpass_url = "http://overpass-api.de/api/interpreter"
    response = requests.get(overpass_url, params={"data": ql_query})
    if response.content:
        try:
            data = response.json()
        except:
            data = {"error": str(response)}
    else:
        data = {
            "Warning": "Received an empty response from Overpass API. Tell the user."
        }
    data_str = json.dumps(data)

    return data_str


# load stops from OSM
def load_osm_result(path):
    with open(path, "r") as f:
        osm_response = json.load(f)

    data = []
    for element in osm_response["elements"]:
        if element["type"] == "node" and "lat" in element and "lon" in element:
            properties = element.get("tags", {})
            properties.update(
                {"id": element["id"], "lat": element["lat"], "lon": element["lon"]}
            )
            data.append(properties)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat))
    gdf.set_crs(epsg=4326, inplace=True)  # Set the CRS to WGS84 (EPSG:4326)
    return gdf


# Define the projection for WGS84 (geographic coordinates)
def transform_latlon_to_gk4_old(latitude, longitude):
    wgs84 = Proj(init="epsg:4326")

    # Define the projection for GK4
    # EPSG code for GK4 (Zone 4) is 31468
    gk4 = Proj(init="epsg:31468")

    # Transform WGS84 to GK4
    x_gk4, y_gk4 = transform(wgs84, gk4, longitude, latitude)
    return x_gk4, y_gk4


wgs84 = "EPSG:4326"
gk4 = "EPSG:31468"
gk4_transformer = Transformer.from_crs(wgs84, gk4)


def transform_latlon_to_gk4(latitude, longitude):
    # wgs84 = Proj(init="epsg:4326")

    # Define the projection for GK4
    # EPSG code for GK4 (Zone 4) is 31468

    # Transform WGS84 to GK4
    x_gk4, y_gk4 = gk4_transformer.transform(latitude, longitude)
    return x_gk4, y_gk4


# point finder for name of stop in vvo
# https://webapi.vvo-online.de/tr/pointfinder
def point_finder_vvo(x_gk4, y_gk4, raw=False):
    url = "https://webapi.vvo-online.de/tr/pointfinder"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    query = f"coord:{round(x_gk4)}:{round(y_gk4)}"
    data = {
        "query": query,
        "stopsOnly": True,
        "regionalOnly": True,
    }
    try:
        r = requests.post(url, headers=headers, data=json.dumps(data))
        if r.status_code == 200:
            # response = json.loads(r.content.decode('utf-8'))
            response = r.json()
        # TODO: no error, but no value?
        else:
            raise requests.HTTPError("HTTP Status: {}".format(r.status_code))
    except requests.RequestException as e:
        print("Failed to access VVO monitor. Request Exception", e)
        response = None

    return_value = None

    # if response is None:
    #     return None
    # return response if raw else [
    #     {
    #         'line': line,
    #         'direction': direction,
    #         'arrival': 0 if arrival == '' else int(arrival)
    #     } for line, direction, arrival in response
    #     ]
    if response is not None and response["Status"]["Code"] == "Ok":
        if len(response["Points"]) > 0:
            closest_point = response["Points"][0].split("|")
            return_value = {
                "stopid": closest_point[0],
                "city": closest_point[2],  # empty if not in VVO
                "stop_name": closest_point[3],
                "x_gk4": closest_point[4],
                "y_gk4": closest_point[5],
            }
    return return_value

    # url = "https://webapi.vvo-online.de/tr/pointfinder"
    # headers = {
    #     "Content-Type": "application/json; charset=utf-8"
    # }
    # data = {
    #     "query": "Albertplatz",
    #     "stopsOnly": True,
    #     "regionalOnly": True,
    # }

    # response = requests.post(url, headers=headers, data=json.dumps(data))

    # print(response.status_code)
    # print(response.json())


# departure monitor for id of stop in vvo
# # url='https://webapi.vvo-online.de/dm'
def departure_monitor(stopid, raw=False):
    url = "https://webapi.vvo-online.de/dm"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "stopid": stopid,
        "mot": [
            "Tram",
            "CityBus",
        ],
    }

    try:
        r = requests.post(url, headers=headers, data=json.dumps(data))
        if r.status_code == 200:
            # response = json.loads(r.content.decode('utf-8'))
            response = r.json()
        # TODO: no error, but no value?
        else:
            raise requests.HTTPError("HTTP Status: {}".format(r.status_code))
    except requests.RequestException as e:
        print("Failed to access VVO monitor. Request Exception", e)
        response = None

    return_value = None

    if response is not None and response["Status"]["Code"] == "Ok":
        if len(response["Departures"]) > 0:
            departures = response["Departures"]
            columns = ["LineName", "Direction", "Platform"]
            return_value = pd.DataFrame(columns=columns)
            for item in response["Departures"]:
                i = return_value.shape[0]
                return_value.loc[i, columns] = [
                    item["LineName"],
                    item["Direction"],
                    item["Platform"]["Name"],
                ]

    return return_value
