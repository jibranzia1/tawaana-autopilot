"""Delete posts from the Tawaana Facebook Page (Instagram's API cannot delete).

    python scripts/delete_fb.py <queue item id> [<queue item id> ...]

Looks up each item's Facebook id in log/published.json, deletes it with the Page token
and records "deleted_at" in the log so the publisher never posts it again.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from publish import GRAPH, LOG, META, TZ, MetaError, call, say  # noqa: E402


def main():
    ids = [i.strip() for a in sys.argv[1:] for i in a.split(",") if i.strip()]
    if not ids:
        sys.exit("give one or more queue item ids")
    token = os.environ.get("META_PAGE_TOKEN", "")
    page = os.environ.get("FB_PAGE_ID") or META.get("facebook_page_id")
    if not token:
        sys.exit("META_PAGE_TOKEN secret is not set")
    page_token = call("GET", f"{GRAPH}/{page}", token, fields="access_token").get("access_token") or token
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    failures = []
    for item in ids:
        fb = log.get(item, {}).get("facebook")
        if not fb or not fb.get("id"):
            failures.append(f"{item}: no Facebook id in the log")
            continue
        if fb.get("deleted_at"):
            say(f"{item}: already deleted")
            continue
        try:
            call("DELETE", f"{GRAPH}/{fb['id']}", page_token)
            fb["deleted_at"] = datetime.now(TZ).isoformat(timespec="seconds")
            say(f"{item}: deleted from Facebook ({fb['id']})")
        except MetaError as e:
            failures.append(f"{item}: {e}")
            say(f"{item}: FAILED {e}")
    LOG.write_text(json.dumps(log, indent=2) + "\n")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
