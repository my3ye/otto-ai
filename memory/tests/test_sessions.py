"""Test session start/end lifecycle."""


def test_session_start_and_end(client):
    # Start a session
    resp = client.post("/sessions/start", json={"session_type": "test"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["id"]
    assert session_id is not None
    assert data["session_type"] == "test"

    # End the session
    resp = client.post(
        f"/sessions/{session_id}/end",
        json={"summary": "test session", "key_decisions": []},
    )
    assert resp.status_code == 200
    end_data = resp.json()
    assert end_data["ended_at"] is not None


def test_last_session(client):
    resp = client.get("/sessions/last")
    assert resp.status_code == 200
    data = resp.json()
    # Should have at least the test session we just created
    assert "id" in data
