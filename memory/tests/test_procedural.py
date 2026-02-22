"""Test procedural memory: create, suggest, outcome, trust_score."""
import uuid


def test_create_procedure(client):
    name = f"test_proc_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/procedural",
        json={
            "name": name,
            "description": "A test procedure",
            "steps": ["step 1", "step 2", "step 3"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == name
    assert data["trust_score"] == 0.5  # default
    assert data["success_count"] == 0
    assert data["failure_count"] == 0


def test_record_success_updates_trust(client):
    name = f"test_trust_{uuid.uuid4().hex[:8]}"
    # Create
    client.post(
        "/procedural",
        json={"name": name, "description": "trust test", "steps": ["s1"]},
    )
    # Record success
    resp = client.put(
        f"/procedural/{name}/outcome",
        json={"success": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success_count"] == 1
    assert data["trust_score"] > 0.5  # should increase


def test_record_failure_decreases_trust(client):
    name = f"test_fail_{uuid.uuid4().hex[:8]}"
    client.post(
        "/procedural",
        json={"name": name, "description": "fail test", "steps": ["s1"]},
    )
    resp = client.put(
        f"/procedural/{name}/outcome",
        json={"success": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["failure_count"] == 1
    assert data["trust_score"] < 0.5  # should decrease


def test_suggest_returns_procedures(client):
    resp = client.get(
        "/procedural/suggest",
        params={"task_description": "build a landing page"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 3


def test_list_procedures(client):
    resp = client.get("/procedural")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
