import argparse
import os
import random
import re
import sys

import folium
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from math import radians, cos, sin, asin, sqrt


def distance_haversine(lt1, ln1, lt2, ln2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    ln1, lt1, ln2, lt2 = map(radians, [ln1, lt1, ln2, lt2])

    # haversine formula
    distance_ln = ln2 - ln1
    distance_lt = lt2 - lt1
    a = sin(distance_lt / 2) ** 2 + cos(lt1) * cos(lt2) * sin(distance_ln / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers.
    return c * r


def arg_parse() -> argparse.Namespace:
    """
    Parse command line arguments. Checks the file for existence
    """
    parser = argparse.ArgumentParser(description="The program generates an HTML map with the closest movie locations to the location specified by the user")
    parser.add_argument("year", type=int, help="Movie launch date")
    parser.add_argument("latitude", type=float, help="Latitude")
    parser.add_argument("longitude", type=float, help="Longitude")
    parser.add_argument("path_to_dataset", type=str, help="Path to dataset")
    args = parser.parse_args()

    if not os.path.exists(args.path_to_dataset):
        print(f"{sys.argv[0]}: error: The specified dataset files does not exist:")
        print(parser.format_usage())
        exit(1)
    return args


def read_data_file(filter_year: int, filename: str) -> list:
    """
    Read ata file
    """
    year_regex = r"\((?P<year>[12][09]\d{2})\)"
    year_regex_compile = re.compile(year_regex)
    with open(filename, "r") as file:
        data = list()
        for line in file:
            line = line.strip()
            if line[-1] == ")":
                bracket = line.rfind('(')
                line = line[:bracket]
            title_and_year, *_, country = line.split("\t")

            if year_regex_compile.search(title_and_year):
                year = year_regex_compile.search(title_and_year).group("year")
                countries = country.split(", ")
                if filter_year == int(year):
                    data.append([title_and_year, countries])
        return data


def get_location_coordinates(data: list, point: tuple) -> list:
    """
    Get location coordinates
    """
    user_lt, user_ln = point
    geo_locator = Nominatim(user_agent="geofilm")
    geo_locator_data = dict()
    reverse = RateLimiter(geo_locator.geocode, min_delay_seconds=3)
    for description, film_point in data:
        while len(film_point) > 1:
            location = reverse(film_point, language='en', exactly_one=True)
            if location is None:
                film_point = film_point[1:]
                continue
            else:
                if (location.latitude, location.longitude) in geo_locator_data:
                    if (geo_locator_data[(location.latitude, location.longitude)][0] != description):
                        latitude = location.latitude + random.random() * 0e-3
                        longitude = location.latitude + random.random() * 0e-3
                else:
                    latitude = location.latitude
                    longitude = location.longitude

                distance = distance_haversine(user_lt, user_ln, latitude, longitude)

                geo_locator_data[(latitude, longitude)] = [description, location, distance]
                break
    sorted_geo_locator_data = sorted(geo_locator_data.items(), key=lambda i: i[1][2])
    return sorted_geo_locator_data[:10]


def map_creation(data: list, year: int, point: tuple) -> None:
    """
    Generate html file
    """
    latitude, longitude = point
    film_map = folium.Map(tiles="Stamen Terrain", location=[latitude, longitude], zoom_start=2)
    customer_feature_group = folium.FeatureGroup(name="Your location")
    customer_feature_group.add_child(folium.Marker(location=[latitude, longitude],popup="Your location",icon=folium.Icon(color="green", icon_color="#FFFF00")))
    film_map.add_child(customer_feature_group)

    film_feature_group = folium.FeatureGroup(name="Тhe film location")
    for point, info in data:
        film_feature_group.add_child(folium.Marker(location=point, popup=f"{info[0]} - {info[1]}", icon=folium.Icon()))
    film_map.add_child(film_feature_group)

    folium.LayerControl().add_to(film_map)
    film_map.save(f"film_map_({year})-({latitude},{longitude}).html")


def main(year: int, latitude: float, longitude: float, path_to_dataset="../locations.list") -> None:
    """
    Create map by CLI args input
    """
    customer_point = latitude, longitude
    data_from_dataset = read_data_file(year, path_to_dataset)
    film_points_data = get_location_coordinates(data_from_dataset, customer_point)
    map_creation(film_points_data, year, customer_point)


if __name__ == "__main__":
    arguments = arg_parse()
    main(**arguments.__dict__)
    # python main.py 2010 49.817545 24.023932 locations100.list
