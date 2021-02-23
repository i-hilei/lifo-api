from flask import Blueprint, request, jsonify
import os
from firebase_admin import firestore

from .download_storage import StorageDownloader
from .tasks import convert_upload_video

storage_page = Blueprint('storage_page', __name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = firestore.client()


@storage_page.route("/brand/storage/download", methods=["POST"])
def storage_download():
    data = request.json
    downloader = StorageDownloader(data)
    downloader.download_files()
    zip_path = downloader.compose_zip()
    download_link = downloader.upload_zip_to_gc(zip_path)

    return jsonify({"link": download_link})


@storage_page.route("/brand/storage/upload-video", methods=["POST"])
def storage_upload():
    video = request.files.get('video')
    blob_name = request.form.get('path')
    campaign_id = request.form.get('campaign_id')
    history_id = request.form.get('history_id')
    if not all([video, blob_name, campaign_id, history_id]):
        return jsonify({"Error": "Please provide all arguments: video, blob, campaign_id, history_id"})
    history = db.collection('campaigns').document(campaign_id).collection('campaignHistory').document(history_id)
    history_doc = history.get()
    history_dict = history_doc.to_dict()
    if not history_dict:
        return jsonify({"Error": f"History of campaign {campaign_id} and history id {history_id} not found."})
    unique_name = blob_name.replace('/', '_')
    file_path = os.path.join(BASE_DIR, 'storage', 'tmp', unique_name)
    video.save(file_path)
    convert_upload_video.delay(blob_name, unique_name, history_id, campaign_id)
    return jsonify({"Success": "Video uploaded."})
