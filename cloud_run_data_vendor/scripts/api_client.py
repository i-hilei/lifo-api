#!/usr/bin/python3

import requests

class ApiClient():
    
    def __init__(self, secure_token_key='AIzaSyBUv4Ms89_KK7nZ_fcw0sBHik23XH_ergA', refresh_token='AE0u-Nd-J72Tyy6x-Oy474EXGplZYW6Q8rCd2vvMmvvpjaNYjgbsIpjYQsyAvAWppZf2EFaAMBXqPYwxzZ86sXJQWrDXkPE66_9KCP8LvJ17NJUwCg6C4S5QWhHL7ntUWkg8LxHNxy3NziCApIV9ElcE1j7TGKF4P3Iy-91TyABJUdLnnGxk-Tgg7It4UDT5FFok_Yb4Hex86JchsO7VmxSpSBnzwRMN0A'):
        url = f'https://securetoken.googleapis.com/v1/token?key={secure_token_key}' 
        headers = { 'Content-Type' : 'application/x-www-form-urlencoded' }
        body = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        res = requests.post(url, data=body, headers=headers)
        print(res.json())
        self.token = res.json()['id_token']
        
    def update_order(self, shopName, campaignId, accountId):
        url = f'https://discover.lifo.ai/brand/update_order'
        headers = { 'Authorization' : self.token}
        payload = {
            'shop': shopName,
            'campaign_id': campaignId,
            'account_id': accountId,
        }
        res = requests.put(url, json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()

    def parse_tracking(self, carrier, tracking_number):
        url = f'https://campaign.lifo.ai/share/track_shipping/{carrier}/{tracking_number}'
        headers = { 'Authorization' : self.token}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data
        else:
            print(f'Failed to obtain tracking information {tracking_number} ({carrier})')
            return None

    def set_shipping_arrived(self, brandCampaignId, accountId):
        url = f'https://campaign.lifo.ai/brand/receive_shipping/brand_campaign_id/{brandCampaignId}/account_id/{accountId}'
        headers = { 'Authorization' : self.token}
        res = requests.put(url, json={}, headers=headers)
        if res.status_code == 200:
            data = res.json()
        else:
            print('error')
    
    def fetch_modash_profile(self, ins_list):
        url = f'https://discover-test.lifo.ai/am/modash/batch_profile?platform=instagram'
        headers = { 'Authorization' : self.token}
        res = requests.post(url, json={
            'influencer_list': ins_list
        }, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data
        else:
            print('error')
            return {}

# client = ApiClient()
# client.update_order('lifo-dev.myshopify.com', 'Cn7nNyxDbFwOKAwH2Bpa', 'lifoinc')
# client.parse_tracking('USPS', '9400111202555764444938')
# client.set_shipping_arrived('Cn7nNyxDbFwOKAwH2Bpa', 'lifoinc')
