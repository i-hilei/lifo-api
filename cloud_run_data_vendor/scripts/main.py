

# To Deploy, Run
# gcloud functions deploy daily_user_summary --entry-point users --runtime python37 --trigger-resource daily_user_summary --trigger-event google.pubsub.topic.publish --timeout 540s
def users(data, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
        data (dict): Event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """
    import users as u
    u.pull_all_users()

# To Deploy, Run
# gcloud functions deploy hourly_notification --entry-point notification --runtime python37 --trigger-resource hourly_notification --trigger-event google.pubsub.topic.publish --timeout 540s
def notification(data, context):
    import notification as n
    n.send_notifications(False)

# To deploy, run 
# gcloud functions deploy daily_campaign_summary --entry-point campaign --runtime python37 --trigger-resource daily_campaign_summary --trigger-event google.pubsub.topic.publish --timeout 540s
def campaign(data, context):
    import campaigns as c
    c.pull_all_campaigns()

def main():
    # users('','')
    notification('','')
    # campaign('', '')
    pass

if __name__ == '__main__':
    main()