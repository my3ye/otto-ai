"""Test cross-brain note creation and retrieval (pending questions flow)."""


def test_create_cross_brain_note(client):
    """Create a gemini_to_claude pending question (cross-brain note)."""
    resp = client.post(
        "/pending/ask",
        json={
            "question": "Test cross-brain note: build a character bible for PiPi",
            "intent": "task",
            "context": "WhatsApp test",
            "channel": "whatsapp",
            "direction": "gemini_to_claude",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] is not None
    note_id = data["id"]

    # Should appear in open pending questions
    resp2 = client.get("/pending/open")
    assert resp2.status_code == 200
    open_notes = resp2.json()
    ids = [n["id"] for n in open_notes]
    assert note_id in ids

    # Resolve it
    resp3 = client.post(
        f"/pending/{note_id}/resolve",
        json={"answer": "Acknowledged — task created for PiPi character bible"},
    )
    assert resp3.status_code == 200
