import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
#app.conf.update(task_serializer="pickle") - alternative way to set celery settings
app.autodiscover_tasks()
