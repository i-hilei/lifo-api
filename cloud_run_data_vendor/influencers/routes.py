from flask import Blueprint, request, render_template, jsonify
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from pandas import read_sql, to_datetime, date_range

from .serializers import UnsubscribedSchema
from .models import Unsubscribed

from database import postgres_db

influencers_page = Blueprint('influencers_page', __name__)


@influencers_page.route("/am/inflluencer/statistics", methods=["GET"])
def influencer_statistics():
    month_ago = datetime.today().date() - timedelta(days=30)
    yesterday = datetime.today().date() - timedelta(days=1)

    query = f'''
    SELECT inf.*, date(public.user.signup_date) as signup_date FROM public.influencer as inf
    INNER JOIN public.user ON inf.id = public.user.id
    WHERE date(public.user.signup_date) <= '{str(yesterday)}'
    '''
    influencers_df = read_sql(query, postgres_db.get_engine())
    influencers_df['signup_date'] = to_datetime(influencers_df['signup_date'])

    dates_range = [str(date).split()[0] for date in date_range(start=month_ago, end=yesterday)]

    aggregation = []
    for date in dates_range:
        this_date_influencers = influencers_df[influencers_df['signup_date'] == date]
        until_this_date_influencers = influencers_df[influencers_df['signup_date'] <= date]

        signed_this_date = len(this_date_influencers)
        total_this_date = len(until_this_date_influencers)
        new_followers = int(this_date_influencers['followers_count'].sum())
        total_followers = int(until_this_date_influencers['followers_count'].sum())

        day_info = {'date': date,
                    'new_influencers': signed_this_date,
                    'total_influencers': total_this_date,
                    'new_followers': new_followers,
                    'total_followers': total_followers}
        aggregation.append(day_info)
    return jsonify(aggregation)


@influencers_page.route("/am/influencer/unsubscribed-list", methods=["GET", "POST"])
def unsubscribed_list():
    if request.method == "GET":
        users_schema = UnsubscribedSchema(many=True)
        users = Unsubscribed.query.all()
        serialized = users_schema.dump(users)
        as_list = [obj['email'] for obj in serialized]
        return jsonify(as_list)

    if request.method == "POST":
        data = request.json
        email = data.get('email')

        if not email:
            return jsonify({"Error": "Email was not provided"}), 400

        new_user = Unsubscribed(email=email)
        try:
            postgres_db.session.add(new_user)
            postgres_db.session.commit()
        except IntegrityError:
            pass
        return render_template('unsubscribed.html')