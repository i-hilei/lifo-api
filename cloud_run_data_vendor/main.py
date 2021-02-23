# -*- coding: utf-8 -*-

import os
import flask
import json
import time
from configparser import ConfigParser
from sys import argv

import requests
from flask import request
from flask_cors import CORS

# Imports the Google Cloud client library
import logging
import google.cloud.logging

from cloud_sql import sql_handler
from scripts.email_sender import EmailSender

from database import postgres_db
from serializing import ma

import firebase_admin
from firebase_admin import auth
from firebase_admin import exceptions
from firebase_admin import firestore

from google.cloud import secretmanager

secrets = secretmanager.SecretManagerServiceClient()
firebase_app = firebase_admin.initialize_app()

# here the db variable is a firestore client. We name it as "db" just to be consistent with JS side.
db = firestore.client()

from labels.routes import labels_page
from storage.routes import storage_page
from influencers.routes import influencers_page
from modash.routes import modash_page
from shopify_lifo.routes import shopify_page
from lists.routes import lists_page
from locations.routes import locations_page
from campaigns.routes import campaigns_page
from shop_products.routes import shop_products_page

config = ConfigParser()

try:
    config.read(f'config/{argv[1]}.conf')
except IndexError:
    print("Command should be of type: python <start file> <config name>. Example: python main.py local")
    exit()
db_creds = config['DB_CREDS']
POSTGRES_USER_CREDS_SECRET = db_creds['USER_CREDS_SECRET']
postgres_user_creds = secrets.access_secret_version(POSTGRES_USER_CREDS_SECRET).payload.data.decode("utf-8")
postgres_user_creds = json.loads(postgres_user_creds)

# Instantiates a client
# (Local Dev)
if argv[1] != 'local':
    client = google.cloud.logging.Client()
    # Connects the logger to the root logging handler; by default this captures
    # all logs at INFO level and higher
    # (Local Dev)
    # client.setup_logging()
    logging.basicConfig(level=logging.INFO)

# This variable specifies the name of a file that contains the OAuth 2.0
# information for this application, including its client_id and client_secret.
# (Local Dev)
CLIENT_SECRETS_FILE = config['GOOGLE_CREDS']['FILE_PATH']

# This is taken from https://marketer.modash.io/developer
modash_api_key_path = 'projects/influencer-272204/secrets/modash-api-access-key/versions/1'
MODASH_API_ACCESS_KEY = secrets.access_secret_version(modash_api_key_path).payload.data.decode("utf-8")
MODASH_API_ENDPINT = "https://api.modash.io/v1"
MODASH_AUTH_HEADER = f'Bearer {MODASH_API_ACCESS_KEY}'
MAX_RESULT_LIMIT = 200

ACCOUNT_MANAGER_FLAG = 'account_manager'
STORE_ACCOUNT = 'store_account'
FROM_SHOPIFY = 'from_shopify'

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

FIELD_DELIMITER = "_"


SEARCHABLE_AUDIENCE_LANGUAGE_PREFIX = 'languages'
SEARCHABLE_AUDIENCE_ETH_PREFIX = 'ethnicities'
SEARCHABLE_AUDIENCE_GENDER_PREFIX = 'genders'
SEARCHABLE_AUDIENCE_CITIES_PREFIX = 'geocities'
SEARCHABLE_AUDIENCE_COUNTRIES_PREFIX = 'geocountries'
SEARCHABLE_AUDIENCE_AGES_PREFIX = 'ages'
SEARCHABLE_AUDIENCE_INTERESTS_PREFIX = 'audience_interests'

SUPPORTED_FIELDS_RANGE_FILTERS = {
    "followers", "engagementRate", "paidPostPerformance"
}

SUPPORTED_FIELDS_CONTAINS_FILTERS = {
    "gender", "interests"
}

SUPPORTED_FILTER_PREFIXES = {
    SEARCHABLE_AUDIENCE_LANGUAGE_PREFIX,
    SEARCHABLE_AUDIENCE_ETH_PREFIX,
    # SEARCHABLE_AUDIENCE_GENDER_PREFIX,
    SEARCHABLE_AUDIENCE_CITIES_PREFIX,
    # SEARCHABLE_AUDIENCE_COUNTRIES_PREFIX,
    # SEARCHABLE_AUDIENCE_AGES_PREFIX,
    # SEARCHABLE_AUDIENCE_INTERESTS_PREFIX
}

DEFFAULT_DATE_RANGE = 90
MAX_SHOPIFY_RESULTS_LIMIT = 200

app = flask.Flask(__name__)

app.register_blueprint(labels_page)
app.register_blueprint(storage_page)
app.register_blueprint(shopify_page)
app.register_blueprint(influencers_page)
app.register_blueprint(modash_page)
app.register_blueprint(lists_page)
app.register_blueprint(locations_page)
app.register_blueprint(campaigns_page)
app.register_blueprint(shop_products_page)

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}'.format(
    user=postgres_user_creds['USER'],
    pwd=postgres_user_creds['PASSWORD'],
    host=db_creds['HOST'],
    port=db_creds['PORT'],
    name=db_creds['DB_NAME']
)
postgres_db.init_app(app)
ma.init_app(app)
CORS(app)
# Note: A secret key is included in the sample so that it works.
# If you use this code in your application, replace this with a truly secret
# key. See https://flask.palletsprojects.com/quickstart/#sessions.
app.secret_key = 'REPLACE ME - this value is here as a placeholder.'

# initialize email sender
SENDGRID_API_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/sendgrid-api-key/versions/4').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_ID = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_id/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_SECRET = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_secret/versions/1').payload.data.decode("utf-8")

emailSender = EmailSender(SENDGRID_API_KEY, NYLAS_OAUTH_CLIENT_ID, NYLAS_OAUTH_CLIENT_SECRET)


def token_verification(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
    except ValueError or exceptions.InvalidArgumentError:
        logging.error('id_token not string or empty or invalid')
        return ''
    except auth.RevokedIdTokenError:
        logging.error('id_token has been revoked')
        return ''
    return decoded_token


def _build_cors_prelight_response():
    response = flask.make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    return response


@app.before_request
def hook():
    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_prelight_response()
    if request.path.startswith('/brand') or request.path.startswith('/am') or request.path.startswith('/influencer'):
        id_token = flask.request.headers.get('Authorization') or flask.request.args.get('id_token')
        if not id_token:
            logging.error('Valid id_token required')
            response = flask.jsonify('Valid id_token required')
            response.status_code = 401
            return response
        decoded_token = token_verification(id_token)
        uid = decoded_token['uid']
        if not uid:
            logging.error('id_token verification failed')
            response = flask.jsonify('id_token verification failed')
            response.status_code = 401
            return response
        logging.info(f'request path is: {request.path} with decoded token {decoded_token}')
        if decoded_token.get(ACCOUNT_MANAGER_FLAG):
            logging.info('AM account has admin access')
        elif not decoded_token.get(ACCOUNT_MANAGER_FLAG) and request.path.startswith('/am'):
            response = flask.jsonify({"status": "not authorized"})
            response.status_code = 403
            return response
        elif (request.path.startswith('/brand') and not decoded_token.get(STORE_ACCOUNT))\
                or (request.path.startswith('/influencer') and decoded_token.get(STORE_ACCOUNT)):
            response = flask.jsonify({"status": "not authorized"})
            response.status_code = 403
            return response

        flask.session['uid'] = uid
        flask.session[FROM_SHOPIFY] = decoded_token.get(FROM_SHOPIFY)
        flask.session[STORE_ACCOUNT] = decoded_token.get(STORE_ACCOUNT)
        flask.session[ACCOUNT_MANAGER_FLAG] = decoded_token.get(ACCOUNT_MANAGER_FLAG)
        flask.session['name'] = decoded_token.get('name')
        flask.session['email'] = decoded_token.get('email')
    else:
        logging.debug(f'By passing auth for request {request.path}')


@app.route("/am/instagram/search", methods=["POST"])
def instagram_search():
    """
        AM use. This is to search instagram account from Modash
    """
    try:
        data = flask.request.json
        url = f'{MODASH_API_ENDPINT}/instagram/search'
        logging.info(f'Receiving request for url {url} and body {data}')
        headers = {'Content-type': 'application/json',
                   'Authorization': MODASH_AUTH_HEADER}
        modash_search = requests.post(url, data=json.dumps(data), headers=headers)
        search_res = modash_search.json()
        logging.info(f'Modash search returned {search_res}')
        if search_res.get('error'):
            logging.error('Search returned error')
            response = flask.jsonify({'Error': 'Failed to search'})
            response.status_code = 400
        else:
            response = flask.jsonify(search_res)
            response.status_code = 200
    except Exception as e:
        logging.error(f'Search error: {e}')
        response = flask.jsonify({'Error': 'Failed to search'})
        response.status_code = 400
    return response


@app.route("/am/modash/search", methods=["POST"])
def modash_search():
    """
        AM use. This is to search instagram account from Modash
    """
    try:
        data = flask.request.json
        platform = flask.request.args.get('platform')
        if platform not in {'instagram', 'tiktok', 'youtube'}:
            response = flask.jsonify({"error": f"{platform} not supported"})
            response.status_code = 422
            return response

        url = f'{MODASH_API_ENDPINT}/{platform}/search'
        logging.info(f'Receiving request for url {url} and body {data}')
        headers = {'Content-type': 'application/json',
                   'Authorization': MODASH_AUTH_HEADER}
        modash_search = requests.post(url, data=json.dumps(data), headers=headers)
        search_res = modash_search.json()
        logging.info(f'Modash search returned {search_res}')
        if search_res.get('error'):
            logging.error('Search returned error')
            response = flask.jsonify({'Error': 'Failed to search'})
            response.status_code = 400
        else:
            fill_influencer_labels(search_res, platform)
            response = flask.jsonify(search_res)
            response.status_code = 200
    except Exception as e:
        logging.error(f'Search error: {e}')
        response = flask.jsonify({'Error': 'Failed to search'})
        response.status_code = 400
    return response


def get_influencer_label(profile, userId, social_platform, campaign_docs, inf_list):
    # Check if registed
    internal_record = db.collection('influencers').where(f'{social_platform}_id', '==', userId).get()
    if len(internal_record) > 0:
        profile['is_registered'] = True
        register_email = ''
        for user in internal_record:
            register_email = user.to_dict()['email']
        profile['register_email'] = register_email
    else:
        profile['is_registered'] = False
    # Fetch additional badges
    profile['complete_campaign'] = False
    profile['in_campaign'] = False
    for campaign in campaign_docs:
        if userId in campaign['inf_campaign_dict'].keys():
            inf_doc = db.collection('brand_campaigns').document(campaign['brand_campaign_id']) \
                        .collection('influencers').document(userId).get()
            if inf_doc.to_dict():
                inf_data = inf_doc.to_dict()
                if 'submit_post_time' in inf_data:
                    profile['complete_campaign'] = True
                if 'offer_accept_time' in inf_data and 'submit_post_time' not in inf_data:
                    profile['in_campaign'] = True
        if profile['in_campaign'] and profile['complete_campaign']:
            break
    profile['in_list'] = True if userId in inf_list else False


def fill_influencer_labels(search_res, social_platform):
    campaign_docs = get_campaign_list()
    inf_list = get_all_list_memeber(social_platform)

    if 'lookalikes' in search_res:
        for inf in search_res['lookalikes']:
            get_influencer_label(inf, inf['profile']['username'], social_platform, campaign_docs, inf_list)

    if 'directs' in search_res:
        for inf in search_res['directs']:
            get_influencer_label(inf, inf['profile']['username'], social_platform, campaign_docs, inf_list)


def process_modash_profile(profile_ref, profile, platform='instagram'):
    account_profile = profile.get('profile')

    interests = profile.get('interests')
    interests_flattened = [pair.get('name') for pair in interests]

    # hashtags are in an array with tuple format, flatten it to collections so that we can sort and filter.
    hashtags = profile.get('hashtags')
    hashtags_flattened = convert_tuple_to_map(hashtags, 'hashtag', 'tag')

    mentions = profile.get('mentions')
    mentions_flattened = convert_tuple_to_map(mentions, 'mention', 'tag')

    # the following three are single valued numerics
    profile_stats = profile.get('stats')
    if profile_stats:
        avg_likes = profile_stats.get('avgLikes').get('value')
        followers = profile_stats.get('followers').get('value')
        paidPostPerformance =profile_stats.get('paidPostPerformance')
    else:
        avg_likes = profile.get('profile').get('engagements')
        followers = profile.get('profile').get('followers')
        paidPostPerformance = profile.get('profile').get('paidPostPerformance')

    # the following audience data needs to be flattened so that it can be easier to query.
    audience = profile.get('audience')
    audience_language = audience.get('languages')
    audience_language_dict = convert_tuple_to_map(audience_language, SEARCHABLE_AUDIENCE_LANGUAGE_PREFIX, 'name')

    audience_ethnicities = audience.get('ethnicities')
    audience_ethnicities_dict = convert_tuple_to_map(audience_ethnicities, SEARCHABLE_AUDIENCE_ETH_PREFIX, 'code')

    audience_credibility = audience.get('credibility')

    audience_genders = audience.get('genders')
    audience_genders_dict = convert_tuple_to_map(audience_genders, 'genders', 'code')

    audience_geoCities = audience.get('geoCities')
    audience_geoCities_dict = convert_tuple_to_map(audience_geoCities, SEARCHABLE_AUDIENCE_CITIES_PREFIX, 'name')

    audience_geoCountries = audience.get('geoCountries')
    audience_geoCountries_dict = convert_tuple_to_map(audience_geoCountries, SEARCHABLE_AUDIENCE_COUNTRIES_PREFIX, 'code')

    # audience_gendersPerAge = audience.get('gendersPerAge')

    audience_ages = audience.get('ages')
    audience_ages_dict = convert_tuple_to_map(audience_ages, SEARCHABLE_AUDIENCE_AGES_PREFIX, 'code')

    audience_interests = audience.get('interests')
    audience_interests_dict = convert_tuple_to_map(audience_interests, SEARCHABLE_AUDIENCE_INTERESTS_PREFIX, 'name')

    trans = db.transaction()

    trans.set(profile_ref, account_profile, merge=True)
    trans.set(profile_ref, hashtags_flattened, merge=True)
    trans.set(profile_ref, mentions_flattened, merge=True)
    trans.set(profile_ref, audience_language_dict, merge=True)
    trans.set(profile_ref, audience_ethnicities_dict, merge=True)
    trans.set(profile_ref, audience_genders_dict, merge=True)
    trans.set(profile_ref, audience_geoCities_dict, merge=True)
    trans.set(profile_ref, audience_geoCountries_dict, merge=True)
    trans.set(profile_ref, audience_ages_dict, merge=True)
    trans.set(profile_ref, audience_interests_dict, merge=True)
    profile_processed = {
        "profile_json": profile,
        "platform": platform,
        "avg_likes": avg_likes,
        "followers": followers,
        "paidPostPerformance": paidPostPerformance,
        "interests": interests_flattened,
        "credibility": audience_credibility
    }

    trans.set(profile_ref, profile_processed, merge=True)
    trans.commit()
    return profile_processed


def convert_tuple_to_map(tag_tuple_list, field_prefix, field_name):
    if tag_tuple_list:
        return dict({f'{field_prefix}{FIELD_DELIMITER}{pair.get(field_name)}': pair.get('weight') for pair in tag_tuple_list})
    return {}


def save_modash_profile_firebase(user_id, profile, platform='instagram'):
    # (10/30) Modash id Can't start and end with double underscores (__)
    if user_id.startswith('__') and user_id.endswith('__'):
        user_id = '@' + user_id
    profile_ref = db.document('modash', user_id)
    profile_processed = process_modash_profile(profile_ref, profile, platform)
    logging.info(f'{user_id} saving processed profile {profile_processed}')


def field_range_filter_handler(modash_profile_ref, field_range_filters):
    pass


def field_contain_filter_handler(modash_profile_ref, field_contain_filters):
    pass


def prefix_filters_handler(modash_profile_ref, prefix_filters):
    """
    The prefix filters have to be supported in SUPPORTED_FILTER_PREFIXES, and only one will be applied
    :param modash_profile_ref:
    :param prefix_filters:
          "prefix_filters": [
                {
                  "prefix": "languages",
                  "value": "Chinese",
                  "min": 0,
                  "max": 0.10
                }
              ]
    :return:
    """
    for filter in prefix_filters:
        cur_prefix = filter.get('prefix')
        cur_value = filter.get('value')
        if not cur_prefix or cur_prefix not in SUPPORTED_FILTER_PREFIXES or not cur_value:
            continue
        field_name = f'{cur_prefix}{FIELD_DELIMITER}{cur_value}'
        logging.info(f'filtering on field: {field_name}')
        cur_min = filter.get('min') or 0
        cur_max = filter.get('max') or 1
        if cur_max > 1:
            cur_max = cur_max/100
        prefix_query = modash_profile_ref.where(field_name, u'>=', cur_min).where(field_name, u'<=', cur_max)
        return prefix_query
    return modash_profile_ref


@app.route("/am/modash/match", methods=["POST"])
def modash_match():
    filters = flask.request.json
    if not filters:
        response = flask.jsonify({"error": "None empty post body required!"})
        response.status_code = 412
        return response
    field_range_filters = filters.get('field_range_filters')
    field_contain_filters = filters.get('field_contain_filters')
    prefix_filters = filters.get('prefix_filters')

    modash_profile_ref = db.collection('modash')
    if field_range_filters:
        logging.warning('Field range filters are not supported in server side')
    modash_profile_ref = prefix_filters_handler(modash_profile_ref, prefix_filters)
    snap_list = modash_profile_ref.limit(1000).get()
    results = [doc.to_dict().get('profile_json') for doc in snap_list]
    response = flask.jsonify(results)
    response.status_code = 200
    return response

def fetch_single_profile(force_update, userId, campaign_docs=[], inf_list=[], social_platform='instagram'):
    profile = None

    if not force_update:
        profile, update_time = sql_handler.get_profile(userId, platform=social_platform)
        logging.info(f'Not forcing profile update, and obtained profile')
    if not profile or len(profile) == 0:
        for i in range(0, 5):
            logging.info(f'Fetching profile from Modash for userid {userId}: # {i+1}th try')
            url = f'{MODASH_API_ENDPINT}/{social_platform}/profile/{userId}/report'
            logging.info(f'Receiving request for url {url}')
            headers = {'Authorization': MODASH_AUTH_HEADER}
            profile_res = requests.get(url, headers=headers)
            profile_json = profile_res.json()
            logging.info(f'Modash {social_platform} profile response is: {profile_res.json()}')
            profile = profile_json.get('profile')
            if profile:
                save_modash_profile_firebase(userId, profile, social_platform)
                sql_handler.save_profile(userId, social_platform, profile)
                break
            else:
                if profile_json.get('code') in ['retry_later', 'handle_not_found']:
                    break
                logging.warning('Modash API not responding, retrying')
                time.sleep(1)
    if profile is not None:
        get_influencer_label(profile, userId, social_platform, campaign_docs, inf_list)
    return profile


def get_all_list_memeber(platform):
    influencer_list = db.collection('influencer_list').stream()
    ins_list = []
    # TODO: Need to handle different platform
    for item in influencer_list:
        item_data = item.to_dict()
        if 'demo' in item_data['name'] or 'test' in item_data['name']:
            continue
        ins_list += item_data['ins_list']
    ins_list = list(set(ins_list))
    return ins_list


def get_campaign_list():
    campaign_data_list = []
    campaign_docs = db.collection('brand_campaigns').stream()
    for campaign in campaign_docs:
        campaign_data = campaign.to_dict()
        if 'deleted' in campaign_data:
            continue
        if 'lifo-dev' in campaign_data['brand'] or 'lifo-demo' in campaign_data['brand'] or 'Test Brand' in campaign_data['brand']:
            continue
        if 'inf_campaign_dict' not in campaign_data:
            continue
        campaign_data_list.append(campaign_data)
    return campaign_data_list


def modash_report(social_platform='instagram'):
    """
    This API pulls instagram, tiktok, YouTube full report from Modash
    https://api.modash.io/v1/{social_platform}/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    userId = flask.request.args.get('userId')
    if not userId:
        response = flask.jsonify({"error": "Valid userId param required!"})
        response.status_code = 412
        return response

    force_update = flask.request.args.get('force_update')
    if not force_update:
        force_update = False

    simple_profile = flask.request.args.get('simple_profile')
    if not simple_profile:
        simple_profile = False

    if simple_profile:
        profile = fetch_single_profile(force_update, userId, [], [], social_platform)
    else:
        campaign_docs = get_campaign_list()
        inf_list = get_all_list_memeber(social_platform)
        profile = fetch_single_profile(force_update, userId, campaign_docs, inf_list, social_platform)

    if profile:
        response = flask.jsonify(profile)
        response.status_code = 200
    else:
        response = flask.jsonify({"error": f"Failed to obtain {social_platform} profile"})
        response.status_code = 400
    return response


def modash_batch_report(social_platform='instagram'):
    body = flask.request.json
    influencer_list = body['influencer_list']
    if not influencer_list or len(influencer_list) <= 0:
        response = flask.jsonify({"error": "Valid influencer ids required!"})
        response.status_code = 412
        return response

    force_update = flask.request.args.get('force_update')
    if not force_update:
        force_update = False

    simple_profile = flask.request.args.get('simple_profile')
    if not simple_profile:
        simple_profile = False

    influencer_profiles = {}
    campaign_docs = get_campaign_list() if not simple_profile else []
    inf_list = get_all_list_memeber(social_platform) if not simple_profile else []
    for userId in influencer_list:
        profile = fetch_single_profile(force_update, userId, campaign_docs, inf_list, social_platform)
        if profile:
            influencer_profiles[userId] = profile
    
    if influencer_profiles:
        response = flask.jsonify(influencer_profiles)
        response.status_code = 200
    else:
        response = flask.jsonify({"error": f"Failed to obtain {social_platform} profile"})
        response.status_code = 400
    return response


@app.route("/am/instagram/profile", methods=["GET"])
def instagram_report():
    """
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    return modash_report('instagram')


@app.route("/influencer/modash/profile", methods=["GET"])
def external_modash_report_api():
    """
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_report(platform)


@app.route("/am/modash/profile", methods=["GET"])
def modash_report_api():
    """
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_report(platform)


@app.route("/am/modash/batch_profile", methods=["POST"])
def modash_batch_report_api():
    """
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_batch_report(platform)


@app.route("/influencer/modash/batch_profile", methods=["POST"])
def external_modash_batch_report_api():
    """
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_batch_report(platform)


@app.route("/influencer/instagram/profile", methods=["GET"])
def instagram_report_influencer():
    """
    We need this endpoint to check if influencer has an Instagram account.
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/instagram/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    return modash_report('instagram')


@app.route("/influencer/modash/profile", methods=["GET"])
def modash_report_influencer():
    """
    We need this endpoint to check if influencer has an Instagram account.
    This API pulls instagram full report from Modash
    https://api.modash.io/v1/modash/profile/{userId}/report
    The default behavior is to use a cached version of report stored in Lifo's SQL server.
    If "force_update" parameter is true, the profile will then be updated, each pull of which costs ~$0.40
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_report(platform)


@app.route("/brand/instagram/interests", methods=["GET"])
def instagram_interests():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~interests/get
    This is to get the brands IDs provided by Modash. Essentially this is getting the enum
    for interests, which will be used for hooking up search functionalities.
    """
    return modash_utils('interests')


@app.route("/brand/modash/interests", methods=["GET"])
def modash_interests():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~interests/get
    This is to get the brands IDs provided by Modash. Essentially this is getting the enum
    for interests, which will be used for hooking up search functionalities.
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_utils('interests', social_platform=platform)


@app.route("/brand/instagram/brands", methods=["GET"])
def instagram_brands():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~brands/get
    This is to get the brands IDs provided by Modash. Essentially this is getting the enum
    for brands, which will be used for hooking up search functionalities.
    """
    return modash_utils('brands')


@app.route("/brand/modash/brands", methods=["GET"])
def modash_brands():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~brands/get
    This is to get the brands IDs provided by Modash. Essentially this is getting the enum
    for brands, which will be used for hooking up search functionalities.
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_utils('brands', social_platform=platform)


@app.route("/brand/instagram/languages", methods=["GET"])
def instagram_languages():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~languages/get
    This is to get the location IDs provided by Modash. Essentially this is getting the enum
    for languages, which will be used for hooking up search functionalities.
    There are so many languages, so it is better to hook up a standard location library and
    use the "query" parameter when calling.
    """
    return modash_utils('languages')


@app.route("/brand/modash/languages", methods=["GET"])
def modash_languages():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~languages/get
    This is to get the location IDs provided by Modash. Essentially this is getting the enum
    for languages, which will be used for hooking up search functionalities.
    There are so many languages, so it is better to hook up a standard location library and
    use the "query" parameter when calling.
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_utils('languages', social_platform=platform)


@app.route("/brand/instagram/locations", methods=["GET"])
def instagram_locations():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~1locations/get
    This is to get the location IDs provided by Modash. Essentially this is getting the enum
    for locations, which will be used for hooking up search functionalities.
    There are so many locations, so it is better to hook up a standard location library and
    use the "query" parameter when calling.
    """
    return modash_utils('locations')


@app.route("/brand/modash/locations", methods=["GET"])
def modash_locations():
    """
    https://docs.modash.io/#tag/Instagram/paths/~1instagram~1locations/get
    This is to get the location IDs provided by Modash. Essentially this is getting the enum
    for locations, which will be used for hooking up search functionalities.
    There are so many locations, so it is better to hook up a standard location library and
    use the "query" parameter when calling.
    """
    platform = flask.request.args.get('platform')
    if platform not in {'instagram', 'tiktok', 'youtube'}:
        response = flask.jsonify({"error": f"{platform} not supported"})
        response.status_code = 422
        return response
    return modash_utils('locations', social_platform=platform)


def modash_utils(endpoint_suffix, social_platform='instagram'):
    try:
        query_string = flask.request.args.get('query')
        limit = flask.request.args.get('limit')
        if not limit:
            limit = MAX_RESULT_LIMIT
        params = {'limit': limit}
        if query_string:
            logging.info(f'{endpoint_suffix} query string: {query_string}')
            params['query'] = query_string
        url = f'{MODASH_API_ENDPINT}/{social_platform}/{endpoint_suffix}'
        logging.info(f'Receiving request for url {url}')
        headers = {'Authorization': MODASH_AUTH_HEADER}
        res = requests.get(url, headers=headers, params=params)
        response = flask.jsonify(res.json())
        response.status_code = 200
        return response
    except Exception as e:
        logging.error(f'{endpoint_suffix} search error: {e}')
        response = flask.jsonify({'Error': f'Failed to find {endpoint_suffix}'})
        response.status_code = 400
    return response


@app.route('/brand/book_demo', methods=['POST'])
def book_demo():
    brand_demo_info = flask.request.json
    email = brand_demo_info['email']
    name = brand_demo_info['name']
    phone_number = brand_demo_info['phone_number']
    send_mail = emailSender.send_book_demo_email(email, name, phone_number)    
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


def save_email_result(campaign_id, account_id, email):
    db.collection('brand_campaigns').document(campaign_id).collection('influencers') \
        .document(account_id).collection('emails').add(email)


@app.route('/am/send_accept_discovery_email', methods=['POST'])
def send_accpet_discovery_email():
    email_data = flask.request.json
    email = email_data['email']
    account_id = email_data['account_id']
    product_name = email_data['product_name']
    campaign_id = email_data['campaign_id']

    send_mail = emailSender.send_accept_discovery_email(email, account_id, product_name, campaign_id)
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        save_email_result(campaign_id, account_id, {
            'type': 'accept_discovery',
            'content': send_mail
        })
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


@app.route('/am/send_draft_approve_email', methods=['POST'])
def send_draft_approve_email():
    email_data = flask.request.json
    email = email_data['email']
    account_id = email_data['account_id']
    product_name = email_data['product_name']
    campaign_id = email_data['campaign_id']
    commission_dollar = email_data['commission_dollar']

    send_mail = emailSender.send_draft_approve_email(email, account_id, product_name, campaign_id, commission_dollar)
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        save_email_result(campaign_id, account_id, {
            'type': 'draft_approve',
            'content': send_mail
        })
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


@app.route('/am/send_commission_issued_email', methods=['POST'])
def send_commission_issued_email():
    email_data = flask.request.json
    email = email_data['email']
    account_id = email_data['account_id']
    product_name = email_data['product_name']
    campaign_id = email_data['campaign_id']
    amount = email_data['amount']

    send_mail = emailSender.send_commission_issued_email(email, account_id, product_name, amount)
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        save_email_result(campaign_id, account_id, {
            'type': 'commission_issued',
            'content': send_mail
        })
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


@app.route('/influencer/send_payment_complete_email', methods=['POST'])
def send_payment_complete_email():
    email_data = flask.request.json
    email = email_data['email']
    account_id = email_data['account_id']
    amount = email_data['amount']

    send_mail = emailSender.send_payment_complete_email(email, account_id, amount)
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


@app.route('/influencer/send_referral_emails', methods=['POST'])
def send_referral_emails():
    # Email information
    email_data = flask.request.json
    referral_link = email_data['invitation_link']
    referee_list = email_data['referee_list']
    test_email = email_data['test_email'] if 'test_email' in email_data else None

    # Get referer information
    user_id = flask.session['uid'] 
    internal_ref= db.collection('influencers').document(user_id).get()
    internal_record = internal_ref.to_dict()
    referer_name = 'Lifo'
    referer_email = 'influencer@lifo.ai'
    if 'name' in internal_record:
        referer_name = internal_record['name']
        if 'last_name' in internal_record:
            referer_name = referer_name + ' ' + internal_record['last_name']
    if 'email' in internal_record:
        referer_email = internal_record['email']

    send_mail = emailSender.send_referral_emails(referee_list, referral_link, referer_name, referer_email, test_email)
    if not send_mail:
        res = {'error': 'email failed to send'}
        response = flask.jsonify(res)
        response.status_code = 400
        return response
    else:
        res = {'status': 'OK'}
        response = flask.jsonify(res)
        response.status_code = 200
        return response


def get_client_secret():
    """
    To enable iam role access (for service accounts) to the secret, run the following:
    gcloud beta secrets add-iam-policy-binding client_secret
    --role roles/secretmanager.secretAccessor
    --member serviceAccount:influencer-272204@appspot.gserviceaccount.com
    :return: content of client secret string
    """

    # GCP project in which to store secrets in Secret Manager.
    project_id = 'influencer-272204'

    # ID of the secret to create.
    secret_id = 'client_secret'

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the parent name from the project.
    # parent = client.project_path(project_id)

    resource_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(resource_name)
    secret_string = response.payload.data.decode('UTF-8')
    return secret_string


def write_client_secret():
    # Writing to sample.json
    if not os.path.exists(CLIENT_SECRETS_FILE):
        json_str = get_client_secret()
        dictionary = json.loads(json_str)

        # Serializing json
        json_object = json.dumps(dictionary, indent=4)
        with open(CLIENT_SECRETS_FILE, "w") as outfile:
            outfile.write(json_object)
            print(f'Sucessfully wrote secret file to {CLIENT_SECRETS_FILE}')
    else:
        print('Client secret file found. Continue')


if __name__ == '__main__':
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = 'True'
    write_client_secret()

    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run('0.0.0.0', 8080, debug=True)
