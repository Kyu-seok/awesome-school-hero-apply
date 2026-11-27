from django.apps import AppConfig


class BackofficeConfig(AppConfig):
    """관리자 페이지(/manage/). manage라 하면 manage.py와 겹쳐서 backoffice다."""

    name = "backoffice"
    verbose_name = "관리자 페이지"
