from django.db import models


class ProgramQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Program(models.Model):
    """교육: 히어로스쿨이 제공하는 하나의 교육 상품."""

    slug = models.SlugField("슬러그", unique=True)
    name = models.CharField("교육명", max_length=100)
    summary = models.CharField("한 줄 소개", max_length=200)
    description = models.TextField("상세 소개", blank=True)
    audience = models.CharField("추천 대상", max_length=200, blank=True)
    class_format = models.CharField("수업 형태 안내", max_length=200, blank=True)
    image = models.ImageField("대표 이미지", upload_to="programs/", blank=True)
    is_published = models.BooleanField("공개 여부", default=False)

    objects = ProgramQuerySet.as_manager()

    class Meta:
        verbose_name = "교육"
        verbose_name_plural = "교육"
        ordering = ["pk"]

    def __str__(self):
        return self.name


class CurriculumItem(models.Model):
    """커리큘럼 항목: 교육의 한 교시."""

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="curriculum", verbose_name="교육"
    )
    period = models.PositiveSmallIntegerField("교시")
    title = models.CharField("제목", max_length=100)
    description = models.TextField("설명", blank=True)

    class Meta:
        verbose_name = "커리큘럼 항목"
        verbose_name_plural = "커리큘럼"
        ordering = ["program", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "period"], name="unique_period_per_program"
            )
        ]

    def __str__(self):
        return f"{self.period}교시 {self.title}"
