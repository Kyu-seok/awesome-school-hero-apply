from django.apps import AppConfig


class ExportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "exports"
    verbose_name = "스프레드시트 내보내기"
