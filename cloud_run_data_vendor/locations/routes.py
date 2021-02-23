from flask import Blueprint, request, jsonify
from google.cloud import secretmanager
from googlemaps import Client

locations_page = Blueprint('locations_page', __name__)

secrets = secretmanager.SecretManagerServiceClient()

# Key for google maps api using
GOOGLE_MAPS_API_KEY = secrets.access_secret_version("projects/influencer-272204/secrets/google-maps-api-key/versions/1").payload.data.decode("utf-8")
gmaps = Client(key=GOOGLE_MAPS_API_KEY)


@locations_page.route("/locations/check-address", methods=["GET"])
def check_address():
    """
    {"in_us": true, "formatted_address": "4345 Central pr. New York, USA"}
    """
    address = request.args.get('input')
    if not address:
        return jsonify({"Error": "Address not provided"}), 400

    response = {
        "in_us": False,
        "formatted_address": None
    }
    geocode_result = gmaps.geocode(address)
    if not geocode_result:
        return jsonify(response)

    response['formatted_address'] = geocode_result[0].get('formatted_address')

    if geocode_result[0].get('address_components'):
        for component in geocode_result[0]['address_components']:
            if component['long_name'] == 'United States':
                response['in_us'] = True
                break
    return jsonify(response)


@locations_page.route("/locations/search-us-city", methods=["GET"])
def search_cities():
    input = request.args.get('input')
    if not input:
        return jsonify({"Error": "Input not provided"}), 400

    search_result = gmaps.places_autocomplete(input, language='en', types='(cities)', components={'country': 'US'})

    response = [comp['description'] for comp in search_result]
    return jsonify(response)
