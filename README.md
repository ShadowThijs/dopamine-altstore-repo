# Dopamine AltStore / SideStore Source

An automatically-updated [AltStore/SideStore](https://sidestore.io) source that tracks
the latest [Dopamine](https://github.com/opa334/Dopamine) jailbreak releases, so you
can install and update Dopamine from SideStore/AltStore without manually downloading
and sideloading the `.ipa`.

The source JSON is generated from the GitHub releases API by [`generate.py`](generate.py),
kept fresh by a GitHub Actions workflow and/or a cron job on this VPS, and served from
GitHub Pages and/or a static server on the VPS.

## Add the source to SideStore / AltStore

1. Open SideStore (or AltStore) → **Sources** → **+**
2. Enter your source URL (see below)
3. Install **Dopamine** from the source. New releases are picked up automatically on
   every refresh — SideStore checks sources when it starts and refreshes your apps,
   so you'll see an update badge when a new version is released.

### Option A — GitHub Pages (recommended)

Push this repository to GitHub, then:

1. In the repo settings: **Settings → Pages → Build and deployment → Source: Deploy from a
   branch → Branch: `main` / `/(root)`** → Save.
2. The workflow (`.github/workflows/update-source.yml`) runs every 6 hours (and on demand
   via **Actions → Update AltStore source → Run workflow**). It queries GitHub for new
   Dopamine releases, regenerates `apps.json`, and commits it.
3. Your source URL is:

   ```
   https://<your-github-username>.github.io/<repo-name>/apps.json
   ```

### Option B — VPS

```bash
sudo ./vps/install.sh https://github.com/<you>/<repo>.git
# optional: sudo ./vps/install.sh <repo-url> http://your-domain-or-ip:8080 8080
```

This clones the repo to `/opt/dopamine-repo`, installs an hourly cron that regenerates
`apps.json` into `/var/www/dopamine-repo`, and starts a tiny static server on port 8080.
Your source URL is printed at the end, e.g. `http://<ip>:8080/apps.json`.

(If the machine has a firewall: `sudo ufw allow 8080/tcp`.)

## How it works

```
Dopamine GitHub release ──► generate.py (GitHub Actions cron / VPS cron)
                              │
                              ▼
                          apps.json  ──►  GitHub Pages  or  VPS :8080
                              │
                              └──────────►  SideStore / AltStore
```

- `generate.py` (Python 3.8+, **stdlib only**, no pip install) fetches all releases with
  an `.ipa` asset, builds the source JSON, and **merges with the previous `apps.json`**
  so the full version history is kept.
- Installations point their `downloadURL` at the official GitHub release download, so no
  IPA is ever stored or mirrored — the source can never go stale because of a missed upload.
- The JSON is written in the AltSource format compatible with both AltStore and SideStore:
  - `versions[]` array (AltStore modern format)
  - legacy top-level `version` / `versionDate` / `downloadURL` / `size` keys mirrored from
    the latest version (SideStore requires a top-level `downloadURL` — see
    [SideStore#735](https://github.com/SideStore/SideStore/issues/735))
  - both `date` and `versionDate` fields per version (ISO 8601)
  - `news[]` entries for each tracked release, deduplicated by identifier

## Configuration

| Flag / env            | Default | Effect |
| --------------------- | ------- | ------ |
| `--source-url <url>`  | (required) | Public URL of the hosted `apps.json` |
| `--prereleases`       | off     | Also include pre-release (beta) versions in the same app listing |
| `--no-news`           | on      | Skip news entries for new releases |
| `GITHUB_TOKEN`        | –       | GitHub token to raise the API rate limit (60 → 5000 req/h) |

The GitHub Actions workflow passes the correct source URL automatically; for the VPS,
`vps/update.sh` reads it from `vps/vps.env` (written by `vps/install.sh`).

## Files

| File | Purpose |
| ---- | ------- |
| `generate.py` | Generates `apps.json` from the GitHub releases API |
| `apps.json` | The generated AltStore/SideStore source |
| `.github/workflows/update-source.yml` | Auto-updates `apps.json` every 6 h |
| `vps/install.sh` | One-time VPS setup (cron + static server) |
| `vps/update.sh` | Re-generates and deploys `apps.json` (run by cron) |

## Troubleshooting

- **"Unable to refresh source" / "The data couldn't be read"** — make sure `apps.json`
  is reachable at the exact URL you added and is served as a `.json` file
  (GitHub Pages and the VPS server both do this correctly).
- **Missing update notifications** — news items default to `notify: false` so you won't
  be spammed; the update still appears in the Updates tab automatically.
- **GitHub API rate limit** — the workflow runs from GitHub's own IPs and the VPS cron
  makes 1 request/hour, well under the unauthenticated limit of 60/hour. If you hit it
  anyway, set a `GITHUB_TOKEN`.
- **Downloads are slow / throttled** — IPAs are downloaded from GitHub's own release
  CDN. This is fine for personal use; mirroring the IPA yourself would require re-hosting
  the file, which this setup deliberately avoids.

## Disclaimer

Dopamine is developed by [opa334](https://github.com/opa334), not by the maintainer of
this source. This repository only mirrors the release metadata; it hosts no code and no
IPA files.
