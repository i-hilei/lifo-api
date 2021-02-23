import firebase_admin
from firebase_admin import auth
from firebase_admin import firestore
import csv
from datetime import datetime
import time

# Change here
FILE_NAME = '/Users/shuoshan/Downloads/influencer_updated.csv'

firebase_app = firebase_admin.initialize_app()
db = firestore.client()

influencer_tofill_map = {}
influencer_uids = {}
influencers = []

# Get authenticated users
# Start listing users from the beginning, 1000 at a time.
page = auth.list_users()
while page:
    for user in page.users:
        creation_time = datetime.utcfromtimestamp(user.user_metadata.creation_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        influencer_uids[user.uid] = {
                'uid': user.uid,
                'register_email': user.email,
                'creation_time': creation_time
            }

    # Get next batch of users.
    page = page.get_next_page()

# Get from doc
influencer_docs = db.collection('influencers').stream()

for influencer in influencer_docs:
    influencer_data = influencer.to_dict()
    if influencer.id not in influencer_uids:
        continue
    influencer_data['uid'] = influencer.id
    influencer_data['register_email'] = influencer_uids[influencer.id]['register_email']
    influencer_data['creation_time'] =  influencer_uids[influencer.id]['creation_time']
    influencers.append(influencer_data)

print(len(influencers))

instagram_name_mapping = {}
tiktok_name_mapping = {}

for inf in influencers:
    # print(inf['uid'])
    fill_data = {}
    accounts = {}
    if 'email' not in inf or inf['email'] is None or inf['email'] == 'None' or inf['email'] == '':
        # print('email missing')
        fill_data['email'] = inf['register_email']

    if 'instagram_id' in inf and inf['instagram_id'] is not None:
        accounts['instagram'] = inf['instagram_id']
        instagram_name_mapping[inf['instagram_id']] = inf['email']
    if 'tiktok_id' in inf and inf['tiktok_id'] is not None:
        accounts['tiktok'] = inf['tiktok_id']
        tiktok_name_mapping[inf['tiktok_id']] = inf['email']
    
    # print(accounts)
    # db.collection('influencers').document(inf['uid']).set({'accounts': accounts}, merge=True)
    # ins = ''
    # if 'instagram_id' not in inf or inf['instagram_id'] == 'None' or inf['instagram_id'] is None or inf['instagram_id'] == '':
    #     if inf['register_email'] in influencer_tofill_map and influencer_tofill_map[inf['register_email']] != '#N/A':
    #         ins = influencer_tofill_map[inf['register_email']]
    # else:
    #     ins = inf['instagram_id']

    # if ins.startswith('@'):
    #     ins = ins[1:]
    # if '/' in ins:
    #     ins = ins.split('/')[-1]
    # ins = ins.lower().strip()
    
    # if 'instagram_id' not in inf or ins != inf['instagram_id']:
    #     fill_data['instagram_id'] = ins
    
    if len(fill_data.keys()) > 0:
        print(fill_data)
        print(inf['uid'])
        db.collection('influencers').document(inf['uid']).set(fill_data, merge=True)

campaign_data_list = []
campaign_docs = db.collection('brand_campaigns').stream()

for campaign in campaign_docs:
    # print(campaign.id)
    campaign_data = campaign.to_dict()

    if 'deleted' in campaign_data:
        continue

    if 'lifo-dev' in campaign_data['brand'] or 'lifo-demo' in campaign_data['brand'] or 'Test Brand' in campaign_data['brand']:
        continue

    campaign_data_list.append(campaign_data)

for campaign_data in campaign_data_list:
    influencer_data_list = []
    influencers =  db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).collection('influencers').stream()

    print(campaign_data['campaign_name'] + ' (' + campaign_data['platform'] + ')')
    platform = campaign_data['platform']
    # print('Campaign name: %s' % campaign_data['campaign_name'])
    for influencer in influencers:
        influencer_data = influencer.to_dict()

        # if 'offer_accept_time' not in influencer_data:
        #     continue
            
        influencer_data_list.append(influencer_data)

    for influencer_data in influencer_data_list:
        regist_email = ''
        if platform == 'instagram' and influencer_data['account_id'] in instagram_name_mapping:
            regist_email = instagram_name_mapping[influencer_data['account_id']]
        if platform == 'tiktok' and influencer_data['account_id'] in tiktok_name_mapping:
            regist_email = tiktok_name_mapping[influencer_data['account_id']]

        if regist_email and influencer_data['email'].lower() != regist_email.lower():
            print('Update email for %s (from %s to %s)' % (influencer_data['account_id'], influencer_data['email'], regist_email))
            db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).collection('influencers').document(influencer_data['account_id']).set({'email': regist_email}, merge=True)