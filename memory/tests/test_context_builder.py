"""Test that context briefing builds without error and includes expected sections."""


def test_context_briefing_returns_data(client):
    resp = client.post(
        "/context/briefing",
        json={"source": "startup"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "identity_facts" in data
    assert "procedures" in data
    assert isinstance(data["procedures"], list)


def test_context_briefing_whatsapp_source(client):
    resp = client.post(
        "/context/briefing",
        json={"source": "whatsapp"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "identity_facts" in data
