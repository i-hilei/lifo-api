
import firebase_admin
from firebase_admin import firestore

from google.cloud import storage

firebase_app = firebase_admin.initialize_app()
db = firestore.client()

storage_client = storage.Client()
bucket = storage_client.bucket('influencer-272204.appspot.com')

def fill_content():
    campaign_data_list = []
    campaign_docs = db.collection('campaigns').stream()

    for campaign in campaign_docs:
        # print(campaign.id)
        campaign_data = campaign.to_dict()
        campaign_data_list.append(campaign_data)

    for campaign_data in campaign_data_list:
        history_doc = db.collection('campaigns').document(campaign_data['campaign_id']).collection('campaignHistory').stream()
        for history in history_doc:
            history_data = history.to_dict()
            if 'content' in history_data:
                content = history_data['content']
                if 'images' in content:
                    for image in content['images']:
                        blob = bucket.get_blob(image['path'][1:])
                        if blob:
                            print(blob.content_type)
                        else: 
                            print('non')
                        # except:
                        #     print('error')
                if 'videos' in content:
                    for video in content['videos']:
                        blob = bucket.get_blob(video['path'][1:])
                        if blob:
                            print(blob.content_type)
                        else: 
                            print('non')

fill_content()
