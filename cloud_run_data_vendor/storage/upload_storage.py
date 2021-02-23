import os
from firebase_admin import initialize_app, storage, firestore
from pathlib import Path
from moviepy.editor import VideoFileClip
from mimetypes import guess_type

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = firestore.client()


class StorageUploader:
    def __init__(self):
        try:
            initialize_app()
        except ValueError:
            pass
        self._bucket = storage.bucket('influencer-272204.appspot.com')
        self._tmp_folder = os.path.join(BASE_DIR, 'storage', 'tmp')

        Path(self._tmp_folder).mkdir(exist_ok=True, parents=True)

    def _convert_to_mp4(self, file_path: str, file_name: str) -> str:
        """
        Converts media file to mp4 format
        @param file_path: path to existing file
        @return: path to converted mp4 file
        """

        clip = VideoFileClip(file_path)
        new_file_name = file_name + '.mp4'
        new_file_path = os.path.join(self._tmp_folder, new_file_name)
        temp_audiofile = os.path.join(self._tmp_folder, file_name + '.mp3')
        clip.write_videofile(new_file_path, temp_audiofile=temp_audiofile)
        os.remove(file_path)
        return new_file_path

    def upload_file(self, blob_name: str, unique_name: str):
        file_path = os.path.join(self._tmp_folder, unique_name)
        file_type = guess_type(file_path)
        if file_type[0] == 'video/mp4':
            file_to_upload = file_path
        else:
            file_to_upload = self._convert_to_mp4(file_path, unique_name)

        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(file_to_upload)
        blob.make_public()
        os.remove(file_to_upload)
        return blob.public_url

    @staticmethod
    def update_campaign_history(blob_name: str, history_id: str, campaign_id: str, media_url: str):
        history = db.collection('campaigns').document(campaign_id).collection('campaignHistory').document(history_id)
        history_doc = history.get()
        history_dict = history_doc.to_dict()
        if not history_dict:
            return f"History of campaign {campaign_id} and history id {history_id} not found."
        content = history_dict.get('content') or {}
        content_videos = []
        if history_dict.get('content'):
            if history_dict['content'].get('videos'):
                content_videos = history_dict['content']['videos']
        content_videos.append({'url': media_url, 'path': blob_name})
        content['videos'] = content_videos
        history.update({'content': content})
        return f"History of campaign {campaign_id} and history id {history_id} successfully updated."
