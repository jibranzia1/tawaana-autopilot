"""Publish today's approved post(s) to Instagram and the Facebook Page.

    python scripts/publish.py                  # post whatever is due today (PKT)
    python scripts/publish.py --dry-run        # check everything, post nothing
    python scripts/publish.py --post-id <id>   # force one post or story (e.g. a missed day)
    python scripts/publish.py --stories midday # publish today's 1 PM story (or "evening" for 8 PM)

Needs env META_PAGE_TOKEN (a Page access token with instagram_content_publish and
pages_manage_posts). Page / IG ids come from config/brand.json or env
FB_PAGE_ID / IG_USER_ID. Each platform is logged separately in log/published.json, so a
rerun only retries what failed and never double-posts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
META = BRAND["meta"]
TZ = ZoneInfo(BRAND.get("timezone", "Asia/Karachi"))
GV = META.get("graph_version", "v24.0")
GRAPH = f"https://graph.facebook.com/{GV}"
GRAPH_VIDEO = f"https://graph-video.facebook.com/{GV}"
LOG = ROOT / "log" / "published.json"


def say(*a):
    print("[publish]", *a, flush=True)


class MetaError(RuntimeError):
    pass


def call(method: str, url: str, token: str, **params):
    params["access_token"] = token
    for attempt in range(4):
        r = requests.request(method, url, data=params if method == "POST" else None,
                             params=params if method == "GET" else None, timeout=120)
        try:
            body = r.json()
        except ValueError:
            body = {"raw": r.text[:300]}
        if r.ok and "error" not in body:
            return body
        err = body.get("error", body)
        transient = r.status_code >= 500 or err.get("is_transient") or err.get("code") in (1, 2, 4, 17, 32, 613)
        if transient and attempt < 3:
            say(f"transient error, retry {attempt + 1}:", err.get("message"))
            time.sleep(10 * (attempt + 1))
            continue
        safe = {k: v for k, v in err.items() if k in ("message", "type", "code", "error_subcode", "error_user_msg")}
        raise MetaError(f"{method} {url.split('?')[0].replace(GRAPH, '')}: {safe}")
    raise MetaError("unreachable")


def check_url(url: str):
    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
    except requests.RequestException as e:
        raise MetaError(f"media not reachable: {url} ({e.__class__.__name__})") from e
    if r.status_code != 200:
        raise MetaError(f"media not reachable yet ({r.status_code}): {url}")


# ------------------------------------------------------------------ Instagram

def ig_wait(container: str, token: str, limit_s: int = 600):
    waited = 0
    while waited < limit_s:
        st = call("GET", f"{GRAPH}/{container}", token, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise MetaError(f"IG container {code}: {st.get('status')}")
        time.sleep(8)
        waited += 8
    raise MetaError("IG container processing timed out")


def ig_publish(post: dict, token: str, ig: str) -> dict:
    cap = post["caption"]
    if post["type"] == "image":
        c = call("POST", f"{GRAPH}/{ig}/media", token, image_url=post["media"][0], caption=cap,
                 **({"alt_text": post["alt_text"]} if post.get("alt_text") else {}))["id"]
    elif post["type"] == "carousel":
        kids = []
        for u in post["media"]:
            kids.append(call("POST", f"{GRAPH}/{ig}/media", token, image_url=u, is_carousel_item="true")["id"])
        for k in kids:
            ig_wait(k, token, 180)
        c = call("POST", f"{GRAPH}/{ig}/media", token, media_type="CAROUSEL", children=",".join(kids),
                 caption=cap)["id"]
    elif post["type"] == "reel":
        args = dict(media_type="REELS", video_url=post["media"][0], caption=cap, share_to_feed="true")
        if post.get("cover"):
            args["cover_url"] = post["cover"]
        c = call("POST", f"{GRAPH}/{ig}/media", token, **args)["id"]
    else:
        raise MetaError(f"unknown type {post['type']}")
    ig_wait(c, token)
    mid = call("POST", f"{GRAPH}/{ig}/media_publish", token, creation_id=c)["id"]
    link = call("GET", f"{GRAPH}/{mid}", token, fields="permalink").get("permalink")
    return {"id": mid, "permalink": link}


# ------------------------------------------------------------------ Facebook Page

def fb_publish(post: dict, token: str, page: str) -> dict:
    msg = post.get("fb_caption") or post["caption"]
    if post["type"] == "image":
        r = call("POST", f"{GRAPH}/{page}/photos", token, url=post["media"][0], caption=msg)
        pid = r.get("post_id") or r["id"]
    elif post["type"] == "carousel":
        ids = [call("POST", f"{GRAPH}/{page}/photos", token, url=u, published="false")["id"] for u in post["media"]]
        attached = {f"attached_media[{i}]": json.dumps({"media_fbid": x}) for i, x in enumerate(ids)}
        pid = call("POST", f"{GRAPH}/{page}/feed", token, message=msg, **attached)["id"]
    elif post["type"] == "reel":
        pid = call("POST", f"{GRAPH_VIDEO}/{page}/videos", token, file_url=post["media"][0],
                   description=msg, title=post.get("title", ""))["id"]
    else:
        raise MetaError(f"unknown type {post['type']}")
    return {"id": pid, "permalink": f"https://www.facebook.com/{pid}"}


# ------------------------------------------------------------------ stories

def ig_story(story: dict, token: str, ig: str) -> dict:
    url = story["media"][0]
    key = "video_url" if story["type"] == "video" else "image_url"
    c = call("POST", f"{GRAPH}/{ig}/media", token, media_type="STORIES", **{key: url})["id"]
    ig_wait(c, token)
    mid = call("POST", f"{GRAPH}/{ig}/media_publish", token, creation_id=c)["id"]
    return {"id": mid}


def fb_story(story: dict, token: str, page: str) -> dict:
    url = story["media"][0]
    if story["type"] == "image":
        photo = call("POST", f"{GRAPH}/{page}/photos", token, url=url, published="false")["id"]
        r = call("POST", f"{GRAPH}/{page}/photo_stories", token, photo_id=photo)
        return {"id": r.get("post_id") or photo}
    start = call("POST", f"{GRAPH}/{page}/video_stories", token, upload_phase="start")
    up = requests.post(start["upload_url"], headers={"Authorization": f"OAuth {token}", "file_url": url}, timeout=300)
    if not up.ok:
        raise MetaError(f"story video upload failed ({up.status_code})")
    r = call("POST", f"{GRAPH}/{page}/video_stories", token, upload_phase="finish", video_id=start["video_id"])
    return {"id": r.get("post_id") or start["video_id"]}


# ------------------------------------------------------------------ main

def load_queue(kind: str = "posts") -> list[dict]:
    items = []
    for q in sorted((ROOT / "queue").glob("*.json")):
        for p in json.loads(q.read_text()).get(kind, []):
            p["_queue"] = q.name
            items.append(p)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--post-id", help="force one post or story id")
    ap.add_argument("--stories", choices=["midday", "evening"], help="publish that story slot instead of the feed post")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in PKT)")
    a = ap.parse_args()

    kind = "stories" if a.stories else "posts"
    now = datetime.now(TZ)
    today = a.date or now.strftime("%Y-%m-%d")
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    items = load_queue(kind)
    if a.post_id:
        items = load_queue("posts") + load_queue("stories")

    def ok(p):
        return p.get("status", "approved") == "approved" and (kind == "posts" or p.get("slot") == a.stories)

    if a.post_id:
        due = [p for p in items if p["id"] == a.post_id]
        if not due:
            sys.exit(f"{a.post_id} not found in queue/")
    else:
        due = [p for p in items if p["date"] == today and ok(p)]
        missed = [p["id"] for p in items if p["date"] < today and ok(p)
                  and not log.get(p["id"], {}).get("instagram") and not log.get(p["id"], {}).get("facebook")]
        if missed:
            say("not auto-posting missed items (run with --post-id to post one):", ", ".join(missed[-5:]))
    if a.dry_run and not due and not a.post_id:
        upcoming = sorted((p for p in items if p["date"] >= today and ok(p)), key=lambda p: p["date"])
        due = upcoming[:1]
        if due:
            say("dry run: nothing due today, checking the next scheduled item:", due[0]["id"])
    if not due:
        say(f"nothing due on {today}" + (f" ({a.stories} story)" if a.stories else ""))
        return

    token = os.environ.get("META_PAGE_TOKEN", "")
    ig = os.environ.get("IG_USER_ID") or META.get("instagram_user_id")
    page = os.environ.get("FB_PAGE_ID") or META.get("facebook_page_id")
    failures = []
    if token and page:
        # confirms the token works and finds the Instagram account linked to the Page
        info = call("GET", f"{GRAPH}/{page}", token, fields="name,instagram_business_account{id,username}")
        linked = info.get("instagram_business_account") or {}
        say("token OK for page:", info.get("name"), "| instagram linked:", linked.get("username") or "none found")
        ig = ig or linked.get("id")

    for p in due:
        is_story = "slot" in p
        say(f"{p['id']} ({'story ' if is_story else ''}{p['type']}, {len(p['media'])} file(s))")
        for u in p["media"] + ([p["cover"]] if p.get("cover") else []):
            check_url(u)
        if a.dry_run:
            say("  dry run: media reachable" + ("" if is_story else f", caption {len(p['caption'])} chars"))
            continue
        if not token:
            sys.exit("META_PAGE_TOKEN secret is not set")
        rec = log.setdefault(p["id"], {})
        targets = []
        if META.get("post_to_instagram", True):
            targets.append(("instagram", (lambda p=p: ig_story(p, token, ig)) if is_story
                            else (lambda p=p: ig_publish(p, token, ig)), ig))
        if META.get("post_to_facebook", True):
            targets.append(("facebook", (lambda p=p: fb_story(p, token, page)) if is_story
                            else (lambda p=p: fb_publish(p, token, page)), page))
        for name, fn, account in targets:
            if rec.get(name):
                say(f"  {name}: already posted, skipping")
                continue
            if not account:
                failures.append(f"{p['id']}/{name}: account id missing in config/brand.json")
                continue
            try:
                res = fn()
                res["at"] = datetime.now(TZ).isoformat(timespec="seconds")
                rec[name] = res
                say(f"  {name}: posted {res.get('permalink') or res.get('id')}")
            except MetaError as e:
                failures.append(f"{p['id']}/{name}: {e}")
                say(f"  {name}: FAILED {e}")
            LOG.parent.mkdir(exist_ok=True)
            LOG.write_text(json.dumps(log, indent=2) + "\n")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
