# Tawaana Autopilot

Daily Instagram + Facebook posting for Tawaana, run from this repo.

## How it runs (fully automatic)

1. **Every day ~10:40 AM PKT:** Claude checks how much content is queued. When 4 days or less are left,
   it plans the next 7–13 days (rules in [PLAYBOOK.md](PLAYBOOK.md)), generates images and Reel clips in
   Higgsfield, writes `briefs/<week>.json` on a `week/<week>` branch and opens a PR.
2. **Automatically:** the *Build week* action renders every slide, Reel and story with the Tawaana fonts and
   colours, commits them to `docs/media/<week>/` and comments a full preview on the PR.
3. **Claude checks and merges:** it reviews every rendered image and video, fixes anything off, and merges
   the PR itself. The PR stays as a record. You get a notification with what was added.
   To stop an item, set its `"status"` to `"skip"` in `queue/<week>.json` on main any time before it posts.
4. **Every day:** the *Publish daily post* action posts a story at ~1 PM, the feed post at ~7:45 PM and
   a story at ~8 PM PKT to Instagram and the Facebook Page, and records each in `log/published.json`.

If a post fails, the action run turns red and GitHub emails you. Re-run it from the Actions tab;
it only retries the platform that failed, so nothing is posted twice.

## Repo map

| Path | What it is |
|---|---|
| `briefs/` | Weekly plans: raw AI media links + on-screen text + captions |
| `queue/` | Built posting queue the publisher reads (one file per week) |
| `docs/media/` | Finished JPGs / MP4s, served publicly by GitHub Pages so Meta can fetch them |
| `scripts/build.py` | Renders slides, covers and Reels (Playwright + ffmpeg) |
| `scripts/publish.py` | Posts to Instagram and Facebook via the Graph API |
| `scripts/validate.py` | Checks sizes, formats, caption length and banned sales words |
| `config/brand.json` | Colours, fonts, Page / Instagram ids, Graph API version |
| `log/published.json` | What was posted, where, and when |

## One-time setup

1. **Meta token:** add a repository secret `META_PAGE_TOKEN` (Settings → Secrets and variables → Actions).
   Use a long-lived Page token for the Tawaana Page with `instagram_basic`, `instagram_content_publish`,
   `pages_manage_posts`, `pages_read_engagement`. Best: a System User token from Meta Business Settings (never expires).
2. **Account ids:** set `facebook_page_id` and `instagram_user_id` in `config/brand.json`
   (or repository variables `FB_PAGE_ID` / `IG_USER_ID`).
3. **GitHub Pages:** Settings → Pages → Deploy from branch → `main` / `/docs`.
4. Test without posting: Actions → *Publish daily post* → Run workflow → tick *dry run*.

## Manual controls

- Post a specific item now: Actions → *Publish daily post* → Run workflow → `post_id`.
- Pause everything: Actions → *Publish daily post* → ⋯ → Disable workflow.
- Turn off one platform: set `post_to_facebook` or `post_to_instagram` to `false` in `config/brand.json`.

Fonts: Jost and Playfair Display (SIL Open Font License), downloaded at build time.
