# !/usr/bin/python3

from api_client import ApiClient
from email_sender import EmailSender
import firebase_admin
from firebase_admin import firestore
from google.cloud import secretmanager
import csv

firebase_app = firebase_admin.initialize_app()
db = firestore.client()

secrets = secretmanager.SecretManagerServiceClient()
SENDGRID_API_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/sendgrid-api-key/versions/5').payload.data.decode("utf-8")
SECURE_TOKEN_KEY = secrets.access_secret_version('projects/influencer-272204/secrets/secure_token_key/versions/1').payload.data.decode("utf-8")
REFRESH_TOKEN = secrets.access_secret_version('projects/influencer-272204/secrets/refresh_token/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_ID = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_id/versions/1').payload.data.decode("utf-8")
NYLAS_OAUTH_CLIENT_SECRET = secrets.access_secret_version('projects/influencer-272204/secrets/nylas_client_secret/versions/1').payload.data.decode("utf-8")

email_sender = EmailSender(SENDGRID_API_KEY, NYLAS_OAUTH_CLIENT_ID, NYLAS_OAUTH_CLIENT_SECRET)

FILE_NAME = '/tmp/email_blash.csv'
HEADER = ['ins_id', 'email', 'result']
BLACK_LIST = ['ome@digitaldoor.co', 'media@tonedermatology.com']

def getEmailAddress(influencer):
    emails = []
    if 'contacts' in influencer:
        for contact in influencer['contacts']:
            if contact['type'] == 'email':
                emails.append(contact['value'])
    return emails

def send_batch_emails(instagram_ids, dry_run=True):
    registered = 0
    not_registered = 0
    has_email = 0
    send_emails = 0
    result = []
    for i in range(0, len(instagram_ids), 20):
        if i % 200 == 0:
            api_client = ApiClient(SECURE_TOKEN_KEY, REFRESH_TOKEN)
            response = email_sender.send_raffle_to_unregistered('lifoinc', 'internal-alert@lifo.ai')
        try:
            ins_profile = api_client.fetch_modash_profile(instagram_ids[i:i+20])
            for instagram_id in ins_profile:
                if ins_profile[instagram_id]['is_registered']:
                    registered += 1
                else:
                    not_registered += 1
                    emails = getEmailAddress(ins_profile[instagram_id])
                    if len(emails) > 0:
                        has_email += 1
                    for email in emails:
                        if not dry_run and email not in BLACK_LIST:
                            response = email_sender.send_bait_email_to_unregistered(instagram_id, email)
                            if response:
                                result.append({'result': response, 'ins_id': instagram_id, 'email': email})
                        send_emails += 1
            print('Total registered %d, not registered %d, has email %d, send emails %d' % (registered, not_registered, has_email, send_emails))
            print('Last ins id is %s' % instagram_id)
        except:
            print('Error getting profile, skip')
    return result

def get_all_ins_ids():
    influencer_list = db.collection('influencer_list').stream()
    ins_list = []
    for item in influencer_list:
        item_data = item.to_dict()
        if 'demo' in item_data['name'] or 'test' in item_data['name']:
            continue
        ins_list += item_data['ins_list']

    ins_list = list(set(ins_list))
    return ins_list

def main():
    # Get all list
    ins_list = sorted(get_all_ins_ids())
    
    # Only send a batch now
    # ins_list = list(filter(lambda x: x < 'd', ins_list))
    print(ins_list)
    print('Getting %d total influencers from list' % len(ins_list))
    
    # Send emails
    result = send_batch_emails(ins_list, True)

    with open(FILE_NAME, 'w', newline='') as csvfile:
        fieldnames = HEADER
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for inf in result:
            writer.writerow(inf)


if __name__ == '__main__':
    main()