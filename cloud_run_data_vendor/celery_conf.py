# To start celery locally. Being in the repository cloud_run_vendor_data in a different terminal execute the command:
# celery  -A celery_conf.celery worker -P eventlet -c 8 --loglevel=INFO

from celery import Celery
from firebase_admin import initialize_app

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

celery = Celery('lifo_api', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

try:
    initialize_app()
except ValueError:
    pass

celery.autodiscover_tasks(['storage'], force=True)
