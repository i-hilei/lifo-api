import firebase_admin
from firebase_admin import auth
from firebase_admin import firestore
import csv
from datetime import datetime
from datetime import date
import time
import base64
from sendgrid.helpers.mail import *
from google.cloud import secretmanager

from email_sender import EmailSender
from api_client import ApiClient

# Change here
HEADER = ['uid', 'register_email', 'creation_time', 'email', 'instagram_id', 'tiktok_id', 'name', 'last_name']
FILE_NAME = '/tmp/influencer.csv'

firebase_app = firebase_admin.initialize_app()

db = firestore.client()
secrets = secretmanager.SecretManagerServiceClient()
SENDGRID_API_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/sendgrid-api-key/versions/5').payload.data.decode("utf-8")
SECURE_TOKEN_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/secure_token_key/versions/1').payload.data.decode("utf-8")
REFRESH_TOKEN = secrets.access_secret_version('projects/influencer-272204/secrets/refresh_token/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_ID = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_id/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_SECRET = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_secret/versions/1').payload.data.decode("utf-8")

api_client = ApiClient(SECURE_TOKEN_KEY, REFRESH_TOKEN)
emailSender = EmailSender(SENDGRID_API_KEY, NYLAS_OAUTH_CLIENT_ID, NYLAS_OAUTH_CLIENT_SECRET)

# email_list = ['7dcadc22a0@s.litmustest.com', '7dcadc22a0@sg3.emailtests.com', '7dcadc22a0@ml.emailtests.com', 
# 'barracuda@barracuda.emailtests.com', 'previews_99@gmx.de', 'litmuscheck01@gmail.com', 
# 'litmuscheck01@yahoo.com', 'litmuscheck02@mail.com', 'litmuscheck02@outlook.com', 'litmuscheck03@emailtests.onmicrosoft.com', 
# 'previews_98@web.de', 'litmuscheck02@mail.ru', 'litmuscheck03@gapps.emailtests.com', 'litmustestprod01@gd-testing.com', 
# 'litmustestprod02@yandex.com', 'litmuscheck002@aol.com']
# email_list = ['ximo.liu@lifo.ai', 'ximo.liu@icloud.com', 'ximo.liu@yahoo.com', 'shanshuo0918@gmail.com']
# for email in email_list:
#     emailSender.send_bait_email_to_unregistered('lifoinc', email)

def pull_all_users():
    all_uids = {}
    influencers = []
    brands = []
    per_day_stats = {}
    miss_count = 0

    # Get authenticated users
    # Start listing users from the beginning, 1000 at a time.
    page = auth.list_users()
    while page:
        for user in page.users:
            # Skip internal testing account
            if user.email and 'lifo.ai' in user.email:
                continue 
            creation_time = datetime.utcfromtimestamp(user.user_metadata.creation_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
            all_uids[user.uid] = {
                    'uid': user.uid,
                    'register_email': user.email,
                    'creation_time': creation_time
                }

        # Get next batch of users.
        page = page.get_next_page()

    # Get from firestore
    influencer_docs = db.collection('influencers').stream()
    fetch_ins_list = []
    for influencer in influencer_docs:
        influencer_data = influencer.to_dict()
        if influencer.id not in all_uids:
            miss_count += 1
            continue
        influencer_data['uid'] = influencer.id
        influencer_data['register_email'] = all_uids[influencer.id]['register_email']
        influencer_data['creation_time'] =  all_uids[influencer.id]['creation_time']
        if 'instagram_id' in influencer_data and influencer_data['instagram_id'] not in fetch_ins_list:
            fetch_ins_list.append(influencer_data['instagram_id'])
        influencers.append(influencer_data)

    brand_docs = db.collection('brands').stream()
    for brand in brand_docs:
        brand_data = brand.to_dict()
        if brand.id not in all_uids:
            print(brand.id)
            miss_count += 1
            continue
        brand_data['uid'] = brand.id
        brand_data['creation_time'] = all_uids[brand.id]['creation_time']
        brands.append(brand_data)

    fetch_ins_data = {}
    for i in range(0, len(fetch_ins_list), 50):
        ins_profile = api_client.fetch_modash_profile(fetch_ins_list[i:i+50])

        for ins_id in ins_profile:
            fetch_ins_data[ins_id] = ins_profile[ins_id]['profile']['followers']
    
    print(fetch_ins_data)

    total_followers = 0
    for key in fetch_ins_data:
        if key not in ['lifoinc', 'instagram']:
            total_followers += fetch_ins_data[key]
        else: 
            fetch_ins_data[key] = 0

    should_skip = True

    for inf in influencers:
        signup_date = inf['creation_time'][0:11]
        follower_count = 0
        if 'instagram_id' in inf and inf['instagram_id']:
            ins_id = inf['instagram_id']
            # Send email
            # if 'email' in inf:
            #     response = emailSender.send_raffle_to_registered(ins_id, inf['email'])
            #     if response:
            #         print('Sending emails to %s (%s)' % (ins_id, inf['email']))
            #         time.sleep(1)
            
            if ins_id in fetch_ins_data:
                follower_count = fetch_ins_data[ins_id]
        
        if signup_date not in per_day_stats:
            per_day_stats[signup_date] = {
                'inf_list': [],
                'brand_list': [],
                'total_followers': 0,
            }
        if inf['uid'] not in per_day_stats[signup_date]['inf_list']:
            per_day_stats[signup_date]['inf_list'].append(inf['uid'])
            per_day_stats[signup_date]['total_followers'] += follower_count

    for brand in brands:
        signup_date = brand['creation_time'][0:11]
        if signup_date not in per_day_stats:
            per_day_stats[signup_date] = {
                'inf_list': [],
                'brand_list': [],
                'total_followers': 0,
            }
        if brand['uid'] not in per_day_stats[signup_date]['brand_list']:
            per_day_stats[signup_date]['brand_list'].append(brand['uid'])

    with open(FILE_NAME, 'w', newline='') as csvfile:
        fieldnames = HEADER
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for inf in influencers:
            writer.writerow(inf)

    with open(FILE_NAME, 'rb') as f:
        data = f.read()
        f.close()
    encoded_file = base64.b64encode(data).decode()

    today = date.today().strftime('%Y-%m-%d')
    user_message = f'''
        <div> Daily Influencer Statistics {today} </div>
        <div> Total <b>{len(influencers)}</b> influencer have signed up </div>
        <div> Total followers <b>{total_followers}</b> </div>
        <div> Total <b>{len(brands)}</b> brands have signed up </div> <br><p></p>
        <div> Daily Statistics </div>
    '''

    days = sorted(per_day_stats.keys())
    for day in days:
        user_message += '<div>Date: %s, Inf Count: %d, Total Followers %d, Brand Count: %d</div>' % (
            day, len(per_day_stats[day]['inf_list']), per_day_stats[day]['total_followers'], len(per_day_stats[day]['brand_list'])
        )
    # attachement = Attachment(
    #     FileContent(encoded_file),
    #     FileName('registered_users.csv'),
    #     FileType('application/csv'),
    #     Disposition('attachment')
    # )
    response = emailSender.send_nylas_email(
        from_email='notifications@lifo.ai',
        from_name = 'Lifo Internal Alert',
        to_emails='internal-alert@lifo.ai',
        subject=f'Daily Influencer Statistics - {today}', 
        html_content=user_message,
        # attachement=attachement
    )

    print('Found %d authenticated users, %d influencers, %d brands , and %d missed uid' 
        % (len(all_uids), len(influencers), len(brands), miss_count))

    # Get follwer count

def set_claims():
    user = auth.get_user_by_email('lifo.affiliate@gmail.com')
    # Add incremental custom claim without overwriting existing claims.
    current_custom_claims = user.custom_claims
    # {'store_account': True, 'from_shopify': False, 'from_amazon': True, 'store_email': 'lifo.affiliate@gmail.com', 'store_name': 'Amazon Product'}
    print(current_custom_claims)
    # current_custom_claims['store_name'] = 'Amazon Top Sellers'
    # auth.set_custom_user_claims(user.uid, current_custom_claims)
    

# set_claims()
# emailSender.send_raffle_to_registered('lifoinc', 'shuo.shan@lifo.ai')
pull_all_users()

