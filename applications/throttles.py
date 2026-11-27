from django.conf import settings
from rest_framework.throttling import AnonRateThrottle


class ApplicationSubmitThrottle(AnonRateThrottle):
    """익명 신청 접수 제한. 비율은 APPLICATION_SUBMIT_THROTTLE_RATE 설정으로 정한다."""

    scope = "application_submit"

    def get_rate(self):
        return settings.APPLICATION_SUBMIT_THROTTLE_RATE
