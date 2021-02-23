# !/usr/bin/python3

import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from api_client import ApiClient
from email_sender import EmailSender
import collections
from google.cloud import secretmanager

firebase_app = firebase_admin.initialize_app()
db = firestore.client()

secrets = secretmanager.SecretManagerServiceClient()
SENDGRID_API_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/sendgrid-api-key/versions/5').payload.data.decode("utf-8")
SECURE_TOKEN_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/secure_token_key/versions/1').payload.data.decode("utf-8")
REFRESH_TOKEN = secrets.access_secret_version('projects/influencer-272204/secrets/refresh_token/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_ID = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_id/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_SECRET = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_secret/versions/1').payload.data.decode("utf-8")

api_client = ApiClient(SECURE_TOKEN_KEY, REFRESH_TOKEN)
email_sender = EmailSender(SENDGRID_API_KEY, NYLAS_OAUTH_CLIENT_ID, NYLAS_OAUTH_CLIENT_SECRET)

def merge_stats(map1, map2):
    result = {}
    for key in map1:
        if key not in map2:
            result[key] = map1[key]
        else:
            result[key] = map1[key] + map2[key]
    for key in map2:
        if key not in map1:
            result[key] = map2[key]
    return result

def merge_daily_stats(map1, map2):
    result = {}
    for day in map1:
        if day not in map2:
            result[day] = map1[day]
        else:
            result[day] = merge_stats(map1[day], map2[day])
    
    for day in map2:
        if day not in map1:
            result[day] = map2[day]
    return result


def pull_campaign_influencers(campaign_data):
    influencer_data_list = []
    influencers =  db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).collection('influencers').stream()

    product_price = 0
    if 'product_price' in campaign_data:
        product_price = float(campaign_data['product_price'])

    for influencer in influencers:
        influencer_data = influencer.to_dict()

        if 'offer_accept_time' not in influencer_data:
            continue
            
        influencer_data_list.append(influencer_data)
    
    per_day_stats = {}
    for influencer_data in influencer_data_list:
        accept_date = datetime.utcfromtimestamp(influencer_data['offer_accept_time']).strftime('%Y-%m-%d')

        accept_commission = 0
        accept_bonus = 0
        if 'accept_commission' in influencer_data:
            accept_commission = float(influencer_data['accept_commission'])
        if 'accept_bonus' in influencer_data:
            accept_bonus = float(influencer_data['accept_bonus'])

        if accept_date not in per_day_stats:
            per_day_stats[accept_date] = {
                'campaign_count': 0,
                'inf_count': 0,
                'gmv': 0
            }
        per_day_stats[accept_date]['inf_count'] += 1
        per_day_stats[accept_date]['gmv'] += (product_price + accept_commission + accept_bonus)
    return per_day_stats


def pull_all_campaigns():
    # Step 1 - Get list of active campaigns
    campaign_data_list = []
    campaign_docs = db.collection('brand_campaigns').stream()

    messages = []

    for campaign in campaign_docs:
        # print(campaign.id)
        campaign_data = campaign.to_dict()

        if 'deleted' in campaign_data:
            continue

        if 'lifo-dev' in campaign_data['brand'] or 'lifo-demo' in campaign_data['brand'] or 'Test Brand' in campaign_data['brand']:
            continue

        # Skip non active campaign
        # if 'active' not in campaign_data:
        #     continue
        
        campaign_data_list.append(campaign_data)

    messages.append('<p>There are <b>%d</b> campaings in total.</p>' % len(campaign_data_list))

    per_day_stats = {}
    for campaign_data in campaign_data_list:
        print('Processing campaign %s (%s), product is %s' % \
            (campaign_data['campaign_name'], campaign_data['brand_campaign_id'], campaign_data['product_name']))
        create_date = str(campaign_data['time_stamp'])[0:10]
        if create_date not in per_day_stats:
            per_day_stats[create_date] = {
                'campaign_count': 0,
                'inf_count': 0,
                'gmv': 0
            }
        per_day_stats[create_date]['campaign_count'] += 1
        per_day_stats = merge_daily_stats(per_day_stats, pull_campaign_influencers(campaign_data))
    
    print(per_day_stats)
    days = sorted(per_day_stats.keys())

    for day in days:
        messages.append('<div>Date: %s, New Campaign Count: %d, New Transaction: %d, GMV: $ %d</div>' % (
            day, per_day_stats[day]['campaign_count'], per_day_stats[day]['inf_count'], per_day_stats[day]['gmv']
        ))

    today = datetime.utcnow().strftime('%Y-%m-%d')
    response = email_sender.send_nylas_email(
        from_email='notifications@lifo.ai',
        from_name = 'Lifo Internal Alert',
        to_emails='internal-alert@lifo.ai',
        subject=f'Daily Campaign Statistics - {today}', 
        html_content=''.join(messages),
        # attachement=attachement
    )


pull_all_campaigns()