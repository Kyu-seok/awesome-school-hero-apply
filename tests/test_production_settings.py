import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.django_db

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_unknown_path_shows_korean_404_page(client):
    response = client.get("/no-such-page/")

    assert response.status_code == 404
    html = response.content.decode()
    assert "페이지를 찾을 수 없습니다" in html
    assert 'href="/"' in html


def _env_example() -> dict[str, str]:
    values = {}
    for line in (REPO_ROOT / ".env.example").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key] = value
    return values


def _run_with_env_example(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **_env_example()}
    env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(50)
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_env_example_passes_django_deploy_checks():
    """`.env.example` 값으로 띄운 설정은 배포 점검을 통과한다.

    HTTPS 리다이렉트(W008)와 HSTS(W004)는 Cloudflare가 맡으므로 남아도 된다.
    """
    result = _run_with_env_example("check", "--deploy")

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    warnings = set(re.findall(r"\((security\.\w+)\)", output))
    assert warnings <= {"security.W004", "security.W008"}, output


def test_env_example_treats_cloudflare_forwarded_https_as_secure():
    """Cloudflare가 붙인 X-Forwarded-Proto: https 요청을 서비스 도메인의 HTTPS 요청으로 본다."""
    script = (
        "from django.test import RequestFactory;"
        "r = RequestFactory().get('/', HTTP_HOST='hero-school.kyuships.com',"
        " HTTP_X_FORWARDED_PROTO='https');"
        "print(r.build_absolute_uri())"
    )

    result = _run_with_env_example("shell", "-c", script)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "https://hero-school.kyuships.com/"
