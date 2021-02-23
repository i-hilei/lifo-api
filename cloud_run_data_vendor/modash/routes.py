from flask import Blueprint, request, jsonify

from .models import ModashProfile
from .query_builder import get_filter_query
from database import postgres_db

modash_page = Blueprint('modash_page', __name__)


@modash_page.route("/am/modash-profile/filter", methods=["GET", "POST"])
def filter_modash_profile():
    engine = postgres_db.get_engine()
    if request.method == "GET":
        args = request.args
        conn = engine.connect()
        related_to = args.get('related_to', 'profile')
        if related_to == 'profile':
            profile_countries_q = "SELECT DISTINCT country FROM public.modash_profile_v1"
            profile_cities_q = "SELECT DISTINCT city FROM public.modash_profile_v1"
            profile_language_q = "SELECT DISTINCT language FROM public.modash_profile_v1"
            profile_gender_q = "SELECT DISTINCT gender FROM public.modash_profile_v1"
            profile_hashtags_q = "SELECT DISTINCT tag FROM public.modash_profile_hashtag"
            profile_countries = [value['country'] for value in conn.execute(profile_countries_q)]
            profile_cities = [value['city'] for value in conn.execute(profile_cities_q)]
            profile_language = [value['language'] for value in conn.execute(profile_language_q)]
            profile_gender = [value['gender'] for value in conn.execute(profile_gender_q)]
            profile_hashtags = [value['tag'] for value in conn.execute(profile_hashtags_q)]
            response = {"profile_countries": profile_countries, "profile_cities": profile_cities,
                        "profile_languages": profile_language, "profile_genders": profile_gender,
                        "profile_hashtags": profile_hashtags}
        else:
            audience_cities_q = "SELECT DISTINCT name FROM public.modash_audience_city"
            audience_languages_q = "SELECT DISTINCT name FROM public.modash_audience_language"
            audience_ethnicities_q = "SELECT DISTINCT name FROM public.modash_audience_ethnicity"
            audience_ages_q = "SELECT DISTINCT code FROM public.modash_audience_age"
            audience_genders_q = "SELECT DISTINCT code FROM public.modash_audience_gender"
            audience_interests_q = "SELECT DISTINCT name FROM public.modash_audience_interest"
            audience_cities = [value['name'] for value in conn.execute(audience_cities_q)]
            audience_languages = [value['name'] for value in conn.execute(audience_languages_q)]
            audience_ethnicities = [value['name'] for value in conn.execute(audience_ethnicities_q)]
            audience_ages = [value['code'] for value in conn.execute(audience_ages_q)]
            audience_genders = [value['code'] for value in conn.execute(audience_genders_q)]
            audience_interests = [value['name'] for value in conn.execute(audience_interests_q)]
            response = {"audience_cities": audience_cities, "audience_languages": audience_languages,
                        "audience_ethnicities": audience_ethnicities, "audience_ages": audience_ages,
                        "audience_genders": audience_genders, "audience_interests": audience_interests}
        return jsonify(response)
    if request.method == "POST":
        count_query = get_filter_query(request.json, count=True)
        query = get_filter_query(request.json)
        try:
            conn = engine.connect()
            total_results = conn.execute(count_query).fetchone()[0]
        except Exception as err:
            return jsonify({"Error": f"Error while reading from db. {err}"})

        try:
            conn = engine.connect()
            result = conn.execute(query)
        except Exception as err:
            return jsonify({"Error": f"Error while reading from db. {err}"})

        influencers = []
        for row in result:
            obj = {
                "account_id": row[0],
                'platform': row[1],
                'followers': row[2],
                'fake_followers': row[3],
                'engagements': row[4],
                'avg_likes': row[5],
                'avg_comments': row[6],
                'gender': row[7],
                'age_group': row[8],
                'country': row[9],
                'city': row[10],
                'language': row[11]
            }
            influencers.append(obj)

        response = {
            "total_results": total_results,
            "page": request.json.get('page') or 1,
            "page_size": request.json.get('page_size') or 15,
            "results": influencers}
        return jsonify(response)


@modash_page.route("/am/modash-profile/update", methods=["PUT"])
def update_modash_profile():
    """
    Input example
    [
        {
            "account_id": "0niedirection",
            "platform": "instagram",
            "is_registered": true
        },
        {
            "account_id": "10busybeesfamily",
            "platform": "instagram",
            "is_registered": false,
            "complete_campaign": true
        },
    ]
    """
    data = request.json
    response = {"updated": [], "not_found": []}
    for update in data:
        update_dict = update.copy()
        account_id = update_dict.pop('account_id')
        platform = update_dict.pop('platform')
        modash_prof = ModashProfile.query.filter_by(account_id=account_id, platform=platform).first()
        if not modash_prof:
            response['not_found'].append(update)
            continue

        for key, value in update_dict.items():
            setattr(modash_prof, key, value)
        postgres_db.session.commit()
        response['updated'].append(update)
    return response
