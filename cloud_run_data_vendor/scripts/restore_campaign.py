
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from api_client import ApiClient
from email_sender import EmailSender
import copy
from datetime import datetime
import pytz
import csv
import copy

# inf_campaign_dict
firebase_app = firebase_admin.initialize_app()
db = firestore.client()

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


    print_data = []
    for campaign_data in campaign_data_list:
        
        campaign_info = {
            'campaing_id': campaign_data['brand_campaign_id'],
            'campaign_name': campaign_data['campaign_name'],
            'brand': campaign_data['brand'],
            'create_time': str(campaign_data['time_stamp'])[0:10]
        }
        # print(campaign_info)
        # platform = 'instagram'
        # if 'platform' in campaign_data:
        #     p = campaign_data['platform']
        #     cid = campaign_data['brand_campaign_id']
        #     print(f'{count}: {p} {cid}')
        #     count = count + 1
        #     if campaign_data['platform'] == '':
        #         platform = 'instagram'
        #     elif campaign_data['platform'] == 'tiktok' or campaign_data['platform'] == 'Tik Tok':
        #         platform = 'tiktok'
        #     elif campaign_data['platform'] == 'Youtube':
        #         platform = 'youtube'
        #     elif campaign_data['platform'] == 'Instagram' or campaign_data['platform'] == 'instagram':
        #         platform = 'instagram'
        #     else:
        #         print('hhhhhh')
        # if platform != campaign_data['platform']:
        #     db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).update({
        #         'platform': platform
        #     })
        # if 'configuration' not in campaign_data and 'discover_configuration' in campaign_data:
        #     print('missing configuration')
        #     print(campaign_data['discover_configuration'])

        #     # Update configuration -> discover_configuration
        #     db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).update({
        #         'configuration': campaign_data['discover_configuration']
        #     })
        
        inf_campaign_dict = {}
        if 'inf_campaign_dict' in campaign_data:
            inf_campaign_dict = campaign_data['inf_campaign_dict']
        existing_count = len(inf_campaign_dict)
        # campaign_info['recruited_count'] = existing_count

        influencer_data_list = []
        influencers =  db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).collection('influencers').stream()

        # print('Campaign name: %s' % campaign_data['campaign_name'])
        for influencer in influencers:
            influencer_data = influencer.to_dict()

            if 'offer_accept_time' not in influencer_data:
                continue
                
            influencer_data_list.append(influencer_data)

        for influencer_data in influencer_data_list:
            account_id = influencer_data['account_id']

            if influencer_data['influencer_address1'] is None or influencer_data['influencer_address1'] == '':
                print('%s - %s - %s' % (campaign_data['brand_campaign_id'], account_id, influencer_data['influencer_address1']))

            # inf_data = copy.deepcopy(campaign_info)
            # inf_data['account_id'] = account_id

            # if 'submit_post_time' in influencer_data:
        
            #     inf_data['submit_post_time'] = datetime.fromtimestamp(influencer_data['submit_post_time'], pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d')
            # inf_data['offer_accept_time'] = datetime.fromtimestamp(influencer_data['offer_accept_time'], pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d')
            # print(inf_data)
            # print_data.append(inf_data)
        #     if account_id not in inf_campaign_dict:
        #         print('missing inf campaing %s' % account_id)

        #         # Create campaign
        #         campaign_ref = db.collection('campaigns').document()
        #         campaign_id = campaign_ref.id
        #         campaign_history_ref = db.collection('campaigns').document(campaign_id).collection('campaignHistory').document()
        #         history_id = campaign_history_ref.id
        #         new_campaign_data = copy.deepcopy(campaign_data)
        #         new_campaign_data['campaign_id'] = campaign_id
        #         new_campaign_data['history_id'] = history_id
        #         new_campaign_data['share_url'] = f'https://login.lifo.ai/app/image-review/{campaign_id}'
        #         campaign_history_ref.set(new_campaign_data)
        #         campaign_ref.set({
        #             'uid': influencer_data['user_id'],
        #             'campaign_id': campaign_id,
        #             'brand_campaign_id': campaign_data['brand_campaign_id'],
        #             'brand': campaign_data['brand']
        #         })
        #         inf_campaign_dict[account_id] = campaign_id
        #     else:
        #         inf_campaign = db.collection('campaigns').document(inf_campaign_dict[account_id]).get()
        #         inf_campaign_data = inf_campaign.to_dict()
        #         if inf_campaign_data['uid'] != account_id:
        #             print('update uid to %s' % account_id)
        #             db.collection('campaigns').document(inf_campaign_dict[account_id]).update({'uid': account_id})


        # if len(inf_campaign_dict) != existing_count:
        #     print(inf_campaign_dict)
        #     db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).update({
        #         'inf_campaign_dict': inf_campaign_dict
        #     })
        
        # print('There are %d recruited influencers in this campaign, %d recruited inf_list' % (len(influencer_data_list), len(inf_campaign_dict)))
        # for influencer_data in influencer_data_list:
        #     print(influencer_data)

    # with open('campaign.csv', 'w', newline='') as csvfile:
    #     fieldnames = ['campaing_id', 'campaign_name', 'brand', 'create_time', 'account_id', 'offer_accept_time', 'submit_post_time']
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

    #     writer.writeheader()
    #     for campaign in print_data:
    #         writer.writerow(campaign)

# pull_all_campaigns()

def pull_all_shops():
    shop_data_list = []
    shop_docs = db.collection('shop').stream()

    messages = []

    for shop in shop_docs:
        # print(campaign.id)
        shop_data = shop.to_dict()
        if len(shop_data['product_list']) > 0:
            print('%s Shop (@%s) %s %d items' % (shop_data['shop_name'], shop_data['instagram_id'], shop_data['shop_id'], len(shop_data['product_list'])))


pull_all_shops()