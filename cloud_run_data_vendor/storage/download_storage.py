import os
from datetime import datetime
from threading import Thread
from shutil import copy2, make_archive, rmtree
from google.api_core.exceptions import NotFound
from firebase_admin import initialize_app, storage
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StorageDownloader:
    def __init__(self, data: list):
        try:
            initialize_app()
        except ValueError:
            pass
        self.bucket = storage.bucket('influencer-272204.appspot.com')
        self.data = data
        self.downloads_folder = os.path.join(BASE_DIR, 'storage', 'downloads')
        self.zips_folder = os.path.join(BASE_DIR, 'storage', 'zips')

        Path(self.downloads_folder).mkdir(exist_ok=True, parents=True)
        Path(self.zips_folder).mkdir(exist_ok=True, parents=True)

    def download_files(self):

        def download_blob(name: str, to_folder: str):
            file_path = os.path.join(to_folder, name.split('/')[-1])
            try:
                blob = self.bucket.blob(name)
                blob.download_to_filename(file_path)
            except NotFound:
                os.remove(file_path)

        existing_folders = os.listdir(self.downloads_folder)

        threads = []
        for infl in self.data:
            folder_name = f"{infl['name']}_{infl['campaign_id']}"
            folder_path = os.path.join(self.downloads_folder, folder_name)
            if folder_name not in existing_folders:
                os.mkdir(folder_path)

            existing_files = os.listdir(folder_path)
            files_to_download = [file for file in infl['file_list'] if file.split('/')[-1] not in existing_files]
            files_to_download = [file[1:] for file in files_to_download if file[0] == '/']

            for file in files_to_download:
                thr = Thread(target=download_blob, args=(file, folder_path))
                thr.start()
                threads.append(thr)

        for thread in threads:
            thread.join(timeout=120)

    def compose_zip(self):
        tmp_dir_name = f"files_{datetime.now()}"
        tmp_dir_path = os.path.join(self.zips_folder, tmp_dir_name)
        zip_name = f"{tmp_dir_name}"
        zip_path = os.path.join(self.zips_folder, zip_name)

        os.mkdir(tmp_dir_path)

        for infl in self.data:
            infl_dir_name = f"{infl['name']}_{infl['campaign_id']}"
            infl_dir_path = os.path.join(tmp_dir_path, infl_dir_name)
            os.mkdir(infl_dir_path)

            for file in infl['file_list']:
                file_name = file.split('/')[-1]
                downloads_path = os.path.join(self.downloads_folder, infl_dir_name, file_name)
                try:
                    copy2(downloads_path, infl_dir_path)
                except FileNotFoundError:
                    pass

        make_archive(zip_path, 'zip', tmp_dir_path)
        rmtree(tmp_dir_path)
        return zip_path + '.zip'

    def upload_zip_to_gc(self, zip_path: str) -> str:
        blob_name = zip_path[zip_path.find('zips'):]
        new_blob = self.bucket.blob(blob_name)
        new_blob.upload_from_filename(zip_path)
        new_blob.make_public()
        self._clear_zips_downloads()
        return new_blob.name

    def _clear_zips_downloads(self):
        for file in os.listdir(self.downloads_folder):
            rmtree(os.path.join(self.downloads_folder, file), ignore_errors=True)

        for file in os.listdir(self.zips_folder):
            os.remove(os.path.join(self.zips_folder, file))
