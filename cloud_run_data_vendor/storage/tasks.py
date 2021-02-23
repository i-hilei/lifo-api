from celery_conf import celery
from .upload_storage import StorageUploader


@celery.task
def convert_upload_video(blob_name: str, unique_name: str, history_id: str, campaign_id: str):
    uploader = StorageUploader()
    media_url = uploader.upload_file(blob_name, unique_name)
    result = uploader.update_campaign_history(blob_name, history_id, campaign_id, media_url)
    return result
