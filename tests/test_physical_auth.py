"""Protocol tests with simulated camera, clock and ESP; no hardware claims."""

from types import SimpleNamespace

import pytest

from services.auth import main, physical


@pytest.fixture
def hardware(clients, monkeypatch):
    clock = [physical.time.time()]
    fake_time = SimpleNamespace(time=lambda: clock[0])
    monkeypatch.setattr(physical, "time", fake_time)
    monkeypatch.setattr(main, "time", fake_time)
    calls = []

    def camera(action, username="", session=""):
        calls.append((action, username, session))
        return {"matched": username == "operator", "enrolled": True}

    monkeypatch.setattr(physical, "camera", camera)
    auth, api = clients
    auth.get("/device/status", headers={"Authorization": "Bearer test-device-key"})
    return auth, api, clock, calls


def identify(auth):
    response = auth.post("/identify", json={"username": "operator"})
    assert response.status_code == 200, response.text
    return response.json()["challenge"]


def password(auth, challenge, value="test-password", username="operator"):
    return auth.post(
        "/token", json={"username": username, "password": value, "challenge": challenge}
    )


def test_full_flow_delay_and_single_use(hardware):
    auth, _, clock, calls = hardware
    challenge = identify(auth)
    assert auth.get(f"/session/{challenge}").json()["phase"] == "password"
    assert physical.led()["mode"] == "green_blink"
    assert password(auth, challenge, username="other").status_code == 403
    assert password(auth, challenge).json()["phase"] == "success"
    assert physical.led()["mode"] == "green"
    assert auth.post(f"/session/{challenge}/complete").status_code == 403
    assert password(auth, challenge).status_code == 403
    clock[0] += 29
    physical.led()
    assert auth.post(f"/session/{challenge}/complete").status_code == 403
    clock[0] += 1
    physical.led()
    response = auth.post(f"/session/{challenge}/complete")
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert physical.led()["mode"] == "off"
    assert any(call[0] == "close" for call in calls)
    assert auth.post(f"/session/{challenge}/complete").status_code == 403


def test_face_rejection_retry_lock_and_persistence(hardware):
    auth, _, clock, _ = hardware
    for attempt in range(2):
        physical.led()
        response = auth.post("/identify", json={"username": "unknown" + str(attempt)})
        challenge = response.json()["challenge"]
        assert auth.get(f"/session/{challenge}").json()["phase"] == "face_rejected"
        assert physical.led()["mode"] == "red"
        clock[0] += 29
        assert auth.get(f"/session/{challenge}").json()["phase"] == "face_rejected"
        clock[0] += 1
        physical.tick()
    blocked = auth.post("/identify", json={"username": "operator"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) == 300
    # Opening a new DB connection retains the kiosk-wide lock, regardless of username.
    with physical.database() as db:
        assert db.execute("SELECT failures FROM kiosk").fetchone()[0] == 2
    clock[0] += 300
    physical.led()
    assert identify(auth)


def test_wrong_password_red_ten_seconds_and_restart(hardware):
    auth, _, clock, _ = hardware
    challenge = identify(auth)
    assert password(auth, challenge, "incorrect").json()["phase"] == "password_rejected"
    assert physical.led()["mode"] == "red_blink"
    assert password(auth, challenge).status_code == 403
    clock[0] += 10
    assert auth.get(f"/session/{challenge}").json()["phase"] == "failed"
    physical.led()
    assert identify(auth) != challenge


def test_device_auth_and_missing_device_fail_closed(hardware, monkeypatch):
    auth, _, _, _ = hardware
    assert auth.get("/device/status").status_code == 401
    monkeypatch.setattr(physical, "device_seen", 0)
    assert auth.post("/identify", json={"username": "operator"}).status_code == 503


def test_camera_failure_cannot_enable_password(hardware, monkeypatch):
    from fastapi import HTTPException

    auth, _, _, _ = hardware

    def unavailable(*args, **kwargs):
        raise HTTPException(503)

    monkeypatch.setattr(physical, "camera", unavailable)
    challenge = identify(auth)
    assert password(auth, challenge).status_code == 403
    assert physical.led()["mode"] == "red"


def test_expiration_releases_camera_without_password(hardware):
    auth, _, clock, calls = hardware
    challenge = identify(auth)
    clock[0] += 91
    physical.tick()
    assert password(auth, challenge).status_code == 403
    assert any(call[0] == "close" for call in calls)


def test_management_revokes_tokens_and_removes_face(hardware):
    auth, api, _, calls = hardware
    admin = {"Authorization": "Bearer " + main.issue("operator", "admin")["access_token"]}
    assert (
        auth.put(
            "/users",
            headers=admin,
            json={"username": "alice", "password": "very-long-test-password"},
        ).status_code
        == 200
    )
    assert auth.post("/users/alice/enroll", headers=admin).status_code == 200
    alice = {"Authorization": "Bearer " + main.issue("alice", "operator")["access_token"]}
    assert auth.get("/users", headers=alice).status_code == 403
    assert api.get("/transactions", headers=alice).status_code == 200
    assert (
        auth.put("/users", headers=admin, json={"username": "alice", "enabled": False}).status_code
        == 200
    )
    assert api.get("/transactions", headers=alice).status_code == 401
    assert auth.delete("/users/alice", headers=admin).status_code == 200
    assert any(call[:2] == ("delete", "alice") for call in calls)
    assert auth.delete("/users/operator", headers=admin).status_code == 400


def test_service_account_cannot_open_backoffice(hardware):
    auth, api, _, _ = hardware
    response = auth.post("/token", json={"username": "recovery-check", "password": "test-password"})
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert api.get("/transactions", headers=headers).status_code == 200
    assert auth.get("/users", headers=headers).status_code == 403


def test_camera_is_serialized(hardware):
    auth, _, _, _ = hardware
    identify(auth)
    assert auth.post("/identify", json={"username": "operator"}).status_code == 409


def test_device_disconnect_prevents_success(hardware):
    auth, _, clock, _ = hardware
    challenge = identify(auth)
    assert password(auth, challenge).json()["phase"] == "success"
    clock[0] += 6
    physical.tick()
    assert auth.get(f"/session/{challenge}").json()["phase"] == "failed"
    assert auth.post(f"/session/{challenge}/complete").status_code == 403
