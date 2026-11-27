# Django가 뜰 때 Celery 앱도 불러와서 @shared_task가 이 앱에 묶이게 한다.
from config.celery import app as celery_app

__all__ = ("celery_app",)
