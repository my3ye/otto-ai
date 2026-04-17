#!/usr/bin/env python3
"""Seed existing roadmap files into project_content DB table."""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Map roadmap files to project_ids
ROADMAP_MAP = {
    "01-webassist.md": ("webassist", "WebAssist Roadmap"),
    "02-oms.md": ("oms", "Otto Management System Roadmap"),
    "03-oneon.md": ("oneon", "ONEON Roadmap"),
    "04-tusita.md": ("tusita", "Tusita Roadmap"),
    "05-otto-travel.md": ("otto-travel", "Otto Travel Roadmap"),
    "06-otto-music.md": ("otto-music", "Otto Music Roadmap"),
    "07-otto-market.md": ("otto-market", "Otto Market Roadmap"),
    "08-otto-properties.md": ("otto-properties", "Otto Properties Roadmap"),
    "09-shakrah.md": ("shakrah", "Shakrah Roadmap"),
    "10-panik.md": ("panik", "Panik Roadmap"),
    "11-koink-koin.md": ("koink", "Koink / $KOIN Roadmap"),
    "12-my3ye.md": ("my3ye", "MY3YE Roadmap"),
    "12-pipi.md": ("pipi", "PiPi Roadmap"),
    "13-s0s-systems.md": ("505-systems", "S0S Systems Roadmap"),
    "14-505-systems.md": ("505-systems", "505 Systems Roadmap"),
    "14-otto-ai.md": ("otto", "Otto AI — Decentralized Intelligence Protocol Roadmap"),
    "15-ottolabs.md": ("ottolabs", "Ottolabs Roadmap"),
}

ROADMAPS_DIR = Path("/home/web3relic/otto/universe/roadmaps")


async def main():
    conn = await asyncpg.connect("postgresql://otto@localhost:5432/memory")
    seeded = 0
    skipped = 0

    for filename, (project_id, title) in ROADMAP_MAP.items():
        path = ROADMAPS_DIR / filename
        if not path.exists():
            print(f"  SKIP {filename} — file not found")
            skipped += 1
            continue

        content = path.read_text()

        # Check if already seeded
        existing = await conn.fetchrow(
            "SELECT id FROM project_content WHERE project_id = $1 AND type = 'roadmap' AND title = $2",
            project_id, title
        )
        if existing:
            print(f"  SKIP {filename} — already seeded")
            skipped += 1
            continue

        await conn.execute(
            """INSERT INTO project_content (project_id, type, title, content, metadata)
               VALUES ($1, 'roadmap', $2, $3, '{"source": "universe/roadmaps", "seeded": true}')""",
            project_id, title, content
        )
        print(f"  SEED {filename} → project:{project_id}")
        seeded += 1

    await conn.close()
    print(f"\nDone. Seeded {seeded}, skipped {skipped}.")


if __name__ == "__main__":
    asyncio.run(main())
