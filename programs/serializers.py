from rest_framework import serializers

from programs.models import CurriculumItem, Program


class CurriculumItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumItem
        fields = ["period", "title", "description"]


class ProgramListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ["slug", "name", "summary", "audience", "class_format", "image"]


class ProgramDetailSerializer(serializers.ModelSerializer):
    curriculum = CurriculumItemSerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = [
            "slug", "name", "summary", "description", "audience", "class_format", "image",
            "curriculum",
        ]
