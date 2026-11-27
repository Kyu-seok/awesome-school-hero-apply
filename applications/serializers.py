from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.settings import api_settings

from applications import services
from applications.models import Application
from programs.models import Program

HONEYPOT_FIELD = "website"


class ApplicationSubmitSerializer(serializers.Serializer):
    """신청 접수 입력. 형식만 확인하고 도메인 규칙은 services.receive_application에 맡긴다."""

    program = serializers.SlugRelatedField(
        slug_field="slug", queryset=Program.objects.all(), help_text="교육 슬러그"
    )
    organization_name = serializers.CharField(max_length=100, label="기관명")
    applicant_name = serializers.CharField(max_length=50, label="신청자 이름")
    applicant_email = serializers.EmailField(label="신청자 이메일")
    applicant_phone = serializers.CharField(max_length=30, label="신청자 연락처")
    target_grade = serializers.CharField(max_length=50, label="수업 대상(학년)")
    class_count = serializers.IntegerField(label="학급 수", help_text="1~35")
    class_type = serializers.ChoiceField(choices=Application.ClassType.choices, label="수업 형태")
    session_count = serializers.IntegerField(min_value=1, label="교시 수 또는 회차 수")
    preferred_class_date = serializers.DateField(
        label="수업 희망일", help_text="오늘(KST)로부터 21일 이후"
    )
    contact_date = serializers.DateField(
        label="연락 가능 날짜", help_text="내일 이후, 수업 희망일 전의 평일"
    )
    request_note = serializers.CharField(
        required=False, allow_blank=True, default="", label="요청 사항"
    )
    privacy_consent = serializers.BooleanField(label="개인정보 수집·이용 동의")
    website = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="사람은 비워 둔다(스팸 방지용 숨김 필드).",
    )

    def create(self, validated_data):
        fields = {k: v for k, v in validated_data.items() if k != HONEYPOT_FIELD}
        try:
            return services.receive_application(**fields)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_as_drf_errors(exc)) from exc

    def to_representation(self, instance):
        return ApplicationReceiptSerializer(instance).data


class ApplicationReceiptSerializer(serializers.ModelSerializer):
    """접수 결과: 신청 ID, 상태, 연락 가능 날짜."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "status", "status_display", "contact_date"]
        read_only_fields = fields


def _as_drf_errors(exc: DjangoValidationError) -> dict[str, list[str]]:
    errors = exc.message_dict
    if NON_FIELD_ERRORS in errors:
        errors[api_settings.NON_FIELD_ERRORS_KEY] = errors.pop(NON_FIELD_ERRORS)
    return errors
