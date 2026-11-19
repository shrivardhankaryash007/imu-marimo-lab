"""Check opt-in configuration and the provider protocol without credentials or network."""

from json import dumps, loads

import pytest

import imu_tutor


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("IMU_TUTOR_BASE_URL", "IMU_TUTOR_MODEL", "IMU_TUTOR_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_unconfigured_and_key_only_remain_off(monkeypatch: pytest.MonkeyPatch) -> None:
    assert imu_tutor.load_settings() is None
    monkeypatch.setenv("IMU_TUTOR_API_KEY", "fixture-key")
    assert imu_tutor.load_settings() is None
    monkeypatch.setenv("IMU_TUTOR_MODEL", "fixture-model")
    with pytest.raises(imu_tutor.TutorUnavailable, match="Set both"):
        imu_tutor.load_settings()


@pytest.mark.parametrize("url", ["http://provider.example/v1", "https://x@y.example/v1"])
def test_rejects_nonlocal_http_and_url_credentials(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("IMU_TUTOR_MODEL", "fixture-model")
    monkeypatch.setenv("IMU_TUTOR_BASE_URL", url)
    with pytest.raises(imu_tutor.TutorUnavailable):
        imu_tutor.load_settings()


def test_local_chat_api_can_run_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMU_TUTOR_MODEL", "fixture-model")
    monkeypatch.setenv("IMU_TUTOR_BASE_URL", "http://127.0.0.1:8080/v1/chat/completions/")
    config = imu_tutor.load_settings()
    assert config is not None
    assert (config.scheme, config.host, config.port) == ("http", "127.0.0.1", 8080)
    assert config.path == "/v1/chat/completions"
    assert not config.api_key


def test_uses_configured_https_provider_and_does_not_follow_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMU_TUTOR_MODEL", "fixture-model")
    monkeypatch.setenv("IMU_TUTOR_BASE_URL", "https://provider.example/api/v1/")
    monkeypatch.setenv("IMU_TUTOR_API_KEY", "fixture-key")
    config = imu_tutor.load_settings()
    assert config is not None and "fixture-key" not in repr(config)

    requests: list[tuple[str, str, dict[str, object], dict[str, str]]] = []
    closed: list[bool] = []
    status = 200

    class FakeResponse:
        @property
        def status(self) -> int:
            return status

        def read(self, amount: int) -> bytes:
            assert amount > 0
            return dumps({"choices": [{"message": {"content": "Example answer."}}]}).encode()

    class FakeConnection:
        def __init__(self, host: str, port: int | None, timeout: int) -> None:
            assert (host, port, timeout) == ("provider.example", None, 60)

        def request(self, method: str, path: str, *, body: str, headers: dict[str, str]) -> None:
            requests.append((method, path, loads(body), headers))

        def getresponse(self) -> FakeResponse:
            return FakeResponse()

        def close(self) -> None:
            closed.append(True)

    monkeypatch.setattr(imu_tutor, "HTTPSConnection", FakeConnection)
    turns = [{"role": "user", "content": "What changed?"}]
    assert imu_tutor.ask_tutor(config, turns) == "Example answer."
    method, path, body, headers = requests[0]
    assert (method, path) == ("POST", "/api/v1/chat/completions")
    assert body == {"model": "fixture-model", "messages": turns, "stream": False}
    assert headers["Authorization"] == "Bearer fixture-key"

    status = 307
    with pytest.raises(imu_tutor.TutorUnavailable, match="HTTP 307"):
        imu_tutor.ask_tutor(config, turns)
    assert len(requests) == len(closed) == 2
