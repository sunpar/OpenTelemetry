from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_auth_api_dockerfile_execs_uvicorn_from_shell():
    dockerfile = (ROOT / "services/auth-api/Dockerfile").read_text()

    assert 'CMD ["sh", "-c", "exec uvicorn app:app --host ${AUTH_API_HOST} --port ${AUTH_API_PORT}"]' in dockerfile
