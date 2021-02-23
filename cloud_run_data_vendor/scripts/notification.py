#!/usr/bin/python3

import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from api_client import ApiClient
from email_sender import EmailSender
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

def get_email_list(campaign_id, account_id):
    emails = db.collection('brand_campaigns').document(campaign_id).collection('influencers') \
        .document(account_id).collection('emails').stream()

    email_list = []
    for email in emails:
        email_data = email.to_dict()
        if 'type' in email_data:
            email_list.append(email_data)
    return email_list

def save_email_result(campaign_id, account_id, email):
    db.collection('brand_campaigns').document(campaign_id).collection('influencers') \
        .document(account_id).collection('emails').add(email)

def email_type_exist(email_list, email_type):
    for email in email_list:
        if email['type'] == email_type:
            return True
    return False

def process_single_influencer(campaign_data, influencer_data, dry_run=True):
    to_email = influencer_data['email']
    account_id = influencer_data['account_id']
    product_name = campaign_data['product_name']
    campaign_id = campaign_data['brand_campaign_id']

    messages = []
    email_list = get_email_list(campaign_id, account_id)

    delivery_deadline = 72
    fast_deliver_window = 48
    if 'configuration' in campaign_data:
        delivery_deadline = int(campaign_data['configuration']['delivery_deadline'])
        fast_deliver_window = int(campaign_data['configuration']['fast_deliver_window'])

    accept_commission = 0
    accept_bonus = 0
    if 'accept_commission' in influencer_data:
        accept_commission = influencer_data['accept_commission']
    if 'accept_bonus' in influencer_data:
        accept_bonus = influencer_data['accept_bonus']

    if 'order' in influencer_data:
        order = influencer_data['order']
        if 'fulfillments' in order and len(order['fulfillments']) == 0:
            api_client.update_order(campaign_data['brand_id'], campaign_data['brand_campaign_id'], influencer_data['account_id'])

    if 'shipping_info' in influencer_data:
        tracking_number = influencer_data['shipping_info']['tracking_number']
        carrier = influencer_data['shipping_info']['carrier']

        # Only check for order not delivered 
        if 'product_received_time' not in influencer_data:
            tracking = api_client.parse_tracking(influencer_data['shipping_info']['carrier'], influencer_data['shipping_info']['tracking_number'])
            if tracking and tracking['status'] == 'delivered':
                api_client.set_shipping_arrived(campaign_data['brand_campaign_id'], influencer_data['account_id'])
                # 2.2 Product Delivered
                # Product status is delivered, product receive time not changed and email not sent
                # In this way, if user manually marked as shipped, we won't send out email 
                if not email_type_exist(email_list, 'product_deliver'):
                    if dry_run:
                        print('New product delivered for %s' % account_id)
                        messages += ['New product delivered for %s' % account_id]
                    else:
                        send_mail = email_sender.send_product_deliver_email(to_email, account_id, product_name, campaign_id, delivery_deadline, accept_bonus, fast_deliver_window)
                        if send_mail:
                            save_email_result(campaign_id, account_id, { 
                                'type': 'product_deliver',
                                'content': send_mail
                            })
                            messages += ['New product delivered for %s' % account_id]
                
            # 2.1 Product Shipped: shipped but not delivered and email not sent yet
            elif tracking and not email_type_exist(email_list, 'product_shipped'):
                if dry_run:
                    print('New product shipped for %s' % account_id)
                    messages += ['New product shipped for %s' % account_id]
                else:
                    send_mail = email_sender.send_product_shipped_email(to_email, account_id, product_name, campaign_id, tracking_number, carrier, delivery_deadline)
                    if send_mail:
                        save_email_result(campaign_id, account_id, { 
                            'type': 'product_shipped',
                            'content': send_mail
                        })
                        messages += ['New product shipped for %s' % account_id]
        else:
            # In this case product delivered
            current_time = datetime.utcnow().timestamp()
            # First, when content is not submitted yet
            if 'content_submit_time' not in influencer_data:
                product_received_time = influencer_data['product_received_time']
                expect_content_submit_time = int(product_received_time) + delivery_deadline * 3600

                # 2.6 Draft Overdue: Send if overdue, but less than 24 hours, still not send draft, also email not sent
                if current_time > expect_content_submit_time:
                    if not email_type_exist(email_list, 'content_overdue'):
                        if dry_run:
                            print('New content overdue for %s' % account_id)
                            messages += ['New content overdue for %s' % account_id]
                        else:
                            send_mail = email_sender.send_content_overdue_email(to_email, account_id, product_name, campaign_id)
                            if send_mail:
                                save_email_result(campaign_id, account_id, { 
                                    'type': 'content_overdue',
                                    'content': send_mail
                                })
                                messages += ['New content overdue for %s' % account_id]
                 # 2.4 Draft content is due soon (24hrs before due time): Send if draft due in 24 hrs, not send draft, also email not send
                elif expect_content_submit_time - current_time < 86400:
                    if not email_type_exist(email_list, 'content_remainder'):
                        if dry_run:
                            print('New content reminder for %s' % account_id)
                            messages += ['New ontent reminder for %s' % account_id]
                        else:
                            send_mail = email_sender.send_content_remainder_email(to_email, account_id, product_name, campaign_id, expect_content_submit_time, accept_commission)
                            if send_mail:
                                save_email_result(campaign_id, account_id, { 
                                    'type': 'content_remainder',
                                    'content': send_mail
                                })
                                messages += ['New content reminder for %s' % account_id]

            # Then if content submited and approved, but 
            elif 'content_approve_time' in influencer_data and 'submit_post_time' not in influencer_data:
                content_approve_time = influencer_data['content_approve_time']
                expect_submit_post_time = content_approve_time + 86400
                if 'post_time' in campaign_data and campaign_data['post_time']:
                    expect_submit_post_time = campaign_data['post_time']
                
                # 2.7 Post Overdue: Send if post overdue but less than 24 hours, still not send post, also email not sent
                if current_time > expect_submit_post_time:
                    if not email_type_exist(email_list, 'post_overdue'):
                        if dry_run:
                            print('New post overdue for %s' % account_id)
                            messages += ['New post overdue for %s' % account_id]
                        else:
                            send_mail = email_sender.send_post_overdue_email(to_email, account_id, product_name, campaign_id)
                            if send_mail:
                                save_email_result(campaign_id, account_id, { 
                                    'type': 'post_overdue',
                                    'content': send_mail
                                })
                                messages += ['New post overdue for %s' % account_id]
                # 2.5 Post content is due soon (2hrs before due time): Send if post due in 24 hrs, not send post, also email not send
                elif expect_submit_post_time - current_time < 7200:
                    if not email_type_exist(email_list, 'post_reminder'):
                        if dry_run:
                            print('New post reminder for %s' % account_id)
                            messages += ['New post reminder for %s' % account_id]
                        else:
                            send_mail = email_sender.send_post_reminder_email(to_email, account_id, product_name, campaign_id, expect_submit_post_time, accept_commission)
                            if send_mail:
                                save_email_result(campaign_id, account_id, { 
                                    'type': 'post_reminder',
                                    'content': send_mail
                                })
                                messages += ['New post reminder for %s' % account_id]

    return messages

def process_single_campaign(campaign_data, dry_run=True):
    # Step 2 - Get accepted influencers from campaign
    influencer_data_list = []
    influencers =  db.collection('brand_campaigns').document(campaign_data['brand_campaign_id']).collection('influencers').stream()

    for influencer in influencers:
        influencer_data = influencer.to_dict()

        if 'offer_accept_time' not in influencer_data:
            continue
            
        influencer_data_list.append(influencer_data)
    
    messages = ['There are %d recruited influencers in this campaign' % (len(influencer_data_list))]
    for influencer_data in influencer_data_list:
        new_message = process_single_influencer(campaign_data, influencer_data, dry_run)
        messages += new_message
    
    return messages


def send_notifications(dry_run=True):
    # Step 1 - Get list of active campaigns
    campaign_data_list = []
    campaign_docs = db.collection('brand_campaigns').stream()

    messages = ['<p>This line is to make sure the email is sent properly.</p>']

    for campaign in campaign_docs:
        # print(campaign.id)
        campaign_data = campaign.to_dict()

        if 'deleted' in campaign_data:
            continue

        if 'lifo-dev' in campaign_data['brand'] or 'lifo-demo' in campaign_data['brand']:
            continue

        # Skip non active campaign
        # if 'active' not in campaign_data:
        #     continue
        
        campaign_data_list.append(campaign_data)

    for campaign_data in campaign_data_list:
        print('Processing campaign %s (%s), product is %s' % \
            (campaign_data['campaign_name'], campaign_data['brand_campaign_id'], campaign_data['product_name']))
        
        new_message = process_single_campaign(campaign_data, dry_run)
        if len(new_message) > 1:
            messages.append('Status update for campaign <b> %s (%s) </b>, product is %s' % (campaign_data['campaign_name'], campaign_data['brand_campaign_id'], campaign_data['product_name']))
            messages += new_message
            messages.append('-------------------------------------------------------------')

    current_time = datetime.utcnow().strftime('%H:%M %m/%d/%y UTC')
    response = email_sender.send_nylas_email(
        from_email='notifications@lifo.ai',
        from_name = 'Lifo Internal Alert',
        to_emails='internal-alert@lifo.ai',
        subject=f'Notification Results - {current_time}',
        html_content='<br>'.join(messages)
    )


