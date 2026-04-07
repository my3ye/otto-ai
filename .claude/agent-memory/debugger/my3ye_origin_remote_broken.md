---
name: my3ye_origin_remote_wrong
description: my3ye-web origin remote pointed to non-existent ottomev/my3ye-web — real repo is PipiAgent/my3ye-web. Caused 60 unpushed commits.
type: project
---

my3ye-web `origin` remote was set to `https://github.com/ottomev/my3ye-web.git` which doesn't exist (returns 404). The actual repo lives at `PipiAgent/my3ye-web`. Pushes to `origin` silently failed, accumulating 60 unpushed commits.

**Why:** The repo was likely created under the PipiAgent GitHub account but the origin remote was never updated from the ottomev URL. A pre-push hook auto-switches gh auth between PipiAgent and ottomev, but it can't fix a wrong remote URL.

**How to apply:** When my3ye-web deployments fail, first check that the remote URL resolves. The canonical remote is `pipiagent` pointing to `PipiAgent/my3ye-web`. Fixed origin on 2026-04-07 to also point there.
