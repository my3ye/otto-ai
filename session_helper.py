#!/usr/bin/env python3
"""Otto Session Helper — CLI for session lifecycle management.

Usage:
    python3 session_helper.py start [--type TYPE]
    python3 session_helper.py end --session-id ID --summary "what happened"
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

API = "http://localhost:8100"


def api(method, path, data=None):
    url = f"{API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"API error: {e.code} {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot reach Otto Memory API at {url}: {e.reason}", file=sys.stderr)
        print("Is the otto-memory service running?", file=sys.stderr)
        sys.exit(1)


def start_session(session_type="claude_code"):
    # Create session
    session = api("POST", "/sessions/start", {"session_type": session_type})
    session_id = session["id"]

    # Get context briefing
    briefing = api("POST", f"/context/briefing?session_id={session_id}")

    # Print session info
    print(f"=== Otto Session Started ===")
    print(f"Session ID: {session_id}")
    print(f"Type: {session_type}")
    print()

    # Print last session summary
    last = briefing.get("last_session")
    if last and last.get("summary"):
        print(f"--- Last Session ---")
        print(f"  {last['summary']}")
        print()

    # Print identity facts
    identity = briefing.get("identity_facts", [])
    if identity:
        print(f"--- Identity ({len(identity)} facts) ---")
        for fact in identity[:5]:
            print(f"  - {fact['content']}")
        print()

    # Print key facts
    facts = briefing.get("high_confidence_facts", [])
    if facts:
        print(f"--- Key Facts ({len(facts)} total) ---")
        for fact in facts[:10]:
            print(f"  [{fact['category']}] {fact['content']}")
        print()

    # Print recent events
    events = briefing.get("recent_events", [])
    if events:
        print(f"--- Recent Events ({len(events)} total) ---")
        for event in events[:5]:
            print(f"  [{event['event_type']}] {event['content']}")
        print()

    # Print procedures
    procs = briefing.get("procedures", [])
    if procs:
        print(f"--- Procedures ({len(procs)} total) ---")
        for proc in procs[:5]:
            rate = ""
            total = proc["success_count"] + proc["failure_count"]
            if total > 0:
                rate = f" ({proc['success_count']}/{total} success)"
            print(f"  - {proc['name']}{rate}")
        print()

    # Graph status
    graph = briefing.get("graph_context", {})
    print(f"Graph: {graph.get('status', 'unknown')}")
    print(f"========================")

    return session_id


def end_session(session_id, summary, key_decisions=None):
    data = {"summary": summary}
    if key_decisions:
        data["key_decisions"] = key_decisions

    session = api("POST", f"/sessions/{session_id}/end", data)

    # Log session end as episodic event
    api("POST", "/episodic/events", {
        "session_id": session_id,
        "content": f"Session ended: {summary}",
        "event_type": "observation",
        "importance": 6,
    })

    print(f"=== Otto Session Ended ===")
    print(f"Session ID: {session_id}")
    print(f"Summary: {summary}")
    if session.get("key_decisions"):
        print(f"Decisions: {', '.join(session['key_decisions'])}")
    print(f"========================")


def main():
    parser = argparse.ArgumentParser(description="Otto Session Helper")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a new session")
    start.add_argument("--type", default="claude_code", help="Session type")

    end = sub.add_parser("end", help="End a session")
    end.add_argument("--session-id", required=True, help="Session UUID")
    end.add_argument("--summary", required=True, help="Session summary")
    end.add_argument("--decisions", nargs="*", help="Key decisions made")

    args = parser.parse_args()

    if args.command == "start":
        start_session(args.type)
    elif args.command == "end":
        end_session(args.session_id, args.summary, args.decisions)


if __name__ == "__main__":
    main()
